"""
Vanna 实例管理器

管理 VannaLegacy 和 Agent 实例的生命周期，提供单例缓存。
"""

from vanna.core import Agent, ToolRegistry
from vanna.core.enhancer import DefaultLlmContextEnhancer
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory

from app.core.config import settings
from app.core.logger import get_logger
from app.services.vanna.base import VannaLegacy, VannaLegacyPGVector, SimpleUserResolver

logger = get_logger(__name__)


class VannaInstanceManager:
    """
    Vanna 实例生命周期管理

    管理 VannaLegacy 和 Agent 实例的创建、缓存和销毁。
    使用单例模式确保同一 dataset 的实例复用。
    """

    # Class-level instance caches
    _legacy_instances: dict = {}  # {collection_name: vanna_instance}
    _agent_instances: dict = {}   # {collection_name: agent_instance}
    _global_chroma_client = None

    @classmethod
    def _get_global_chroma_client(cls):
        """
        获取全局单例 ChromaDB 客户端，确保所有实例使用相同配置
        """
        if cls._global_chroma_client is None:
            import chromadb
            cls._global_chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
            logger.info(f"Initialized global ChromaDB client at {settings.CHROMA_PERSIST_DIR}")
        return cls._global_chroma_client

    @classmethod
    def get_legacy_vanna(cls, dataset_id: int):
        """
        Initialize and return a Legacy Vanna instance for SQL generation.
        Supports both ChromaDB and PGVector backends based on configuration.
        Reuses existing client if already created to avoid conflicts.
        """
        collection_name = f"vec_ds_{dataset_id}"

        # Return cached instance if exists
        if collection_name in cls._legacy_instances:
            logger.debug(f"Reusing existing Vanna instance for collection {collection_name}")
            return cls._legacy_instances[collection_name]

        # Check which vector store to use
        vector_store_type = settings.VECTOR_STORE_TYPE.lower()

        if vector_store_type == "pgvector":
            # Use PGVector backend
            logger.info(f"Using PGVector backend for collection {collection_name}")
            vn = VannaLegacyPGVector(
                config={
                    'api_key': settings.DASHSCOPE_API_KEY,
                    'model': settings.QWEN_MODEL,
                    'n_results': settings.CHROMA_N_RESULTS,
                    'collection_name': collection_name,
                    'connection_string': settings.VN_PG_CONNECTION_STRING,
                    'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1'
                }
            )
        else:
            # Use ChromaDB backend (default)
            logger.info(f"Using ChromaDB backend for collection {collection_name}")
            global_client = cls._get_global_chroma_client()
            vn = VannaLegacy(
                config={
                    'api_key': settings.DASHSCOPE_API_KEY,
                    'model': settings.QWEN_MODEL,
                    'n_results': settings.CHROMA_N_RESULTS,
                    'collection_name': collection_name,
                    'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1'
                },
                chroma_client=global_client
            )

        # Enable data visibility for LLM to support intermediate_sql reasoning
        vn.allow_llm_to_see_data = True

        # Cache the instance
        cls._legacy_instances[collection_name] = vn
        logger.info(f"Created new Vanna instance for collection {collection_name} (backend: {vector_store_type})")

        return vn

    @classmethod
    def get_agent(cls, dataset_id: int):
        """
        Initialize and return a configured Vanna Agent instance (Vanna 2.0).
        Reuses existing agent if already created to avoid ChromaDB conflicts.
        """
        collection_name = f"vec_ds_{dataset_id}"

        # Return cached agent if exists
        if collection_name in cls._agent_instances:
            logger.debug(f"Reusing existing Agent instance for collection {collection_name}")
            return cls._agent_instances[collection_name]

        # 1. LLM Service (Qwen via OpenAI compatible API)
        llm_service = OpenAILlmService(
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.QWEN_MODEL,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # 2. Agent Memory (ChromaDB)
        agent_memory = ChromaAgentMemory(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=collection_name
        )

        # 3. Tool Registry
        registry = ToolRegistry()
        # Register SQL tools if needed for querying.
        # For now, we focus on training (memory population).

        # 4. Context Enhancer
        # Injects relevant DDL/Docs from memory into System Prompt
        enhancer = DefaultLlmContextEnhancer(agent_memory=agent_memory)

        # 5. Create Agent
        agent = Agent(
            llm_service=llm_service,
            tool_registry=registry,
            user_resolver=SimpleUserResolver(),
            agent_memory=agent_memory,
            llm_context_enhancer=enhancer
        )

        # Cache the agent instance
        cls._agent_instances[collection_name] = agent
        logger.info(f"Created new Agent instance for collection {collection_name}")

        return agent

    @classmethod
    def delete_collection(cls, dataset_id: int) -> bool:
        """
        删除 Vanna 中指定 dataset 的 collection
        支持 ChromaDB 和 PGVector 两种后端，根据配置自动选择

        Args:
            dataset_id: 数据集ID

        Returns:
            bool: 是否成功删除
        """
        collection_name = f"vec_ds_{dataset_id}"

        try:
            # 1. 从缓存中移除
            if collection_name in cls._legacy_instances:
                del cls._legacy_instances[collection_name]
                logger.info(f"Removed Vanna instance from cache: {collection_name}")

            if collection_name in cls._agent_instances:
                del cls._agent_instances[collection_name]
                logger.info(f"Removed Agent instance from cache: {collection_name}")

            # 2. 根据配置选择删除方式
            vector_store_type = settings.VECTOR_STORE_TYPE.lower()

            if vector_store_type == "pgvector":
                return cls._delete_pgvector_collection(collection_name)
            else:
                return cls._delete_chromadb_collection(collection_name)

        except Exception as e:
            logger.error(f"Failed to delete collection for dataset {dataset_id}: {e}")
            return False

    @classmethod
    def _delete_chromadb_collection(cls, collection_name: str) -> bool:
        """
        删除 ChromaDB 中的 collection

        Args:
            collection_name: collection 名称

        Returns:
            bool: 是否成功删除
        """
        try:
            chroma_client = cls._get_global_chroma_client()

            # 删除所有相关 collection（ddl, documentation, sql）
            for suffix in ['_ddl', '_documentation', '_sql', '']:
                try:
                    chroma_client.delete_collection(name=f"{collection_name}{suffix}")
                    logger.info(f"Deleted ChromaDB collection: {collection_name}{suffix}")
                except Exception as e:
                    if "does not exist" not in str(e).lower():
                        logger.warning(f"Failed to delete collection {collection_name}{suffix}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collections for {collection_name}: {e}")
            return False

    @classmethod
    def _delete_pgvector_collection(cls, collection_name: str) -> bool:
        """
        删除 PGVector 中的 collection

        Args:
            collection_name: collection 名称

        Returns:
            bool: 是否成功删除
        """
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(settings.VN_PG_CONNECTION_STRING)

            # 删除 langchain_pg_embedding 表中的相关记录
            # PGVector 使用 langchain_pg_collection 和 langchain_pg_embedding 表
            with engine.connect() as conn:
                for suffix in ['_ddl', '_documentation', '_sql']:
                    coll_name = f"{collection_name}{suffix}"
                    try:
                        # 先获取 collection uuid
                        result = conn.execute(
                            text("SELECT uuid FROM langchain_pg_collection WHERE name = :name"),
                            {"name": coll_name}
                        )
                        row = result.fetchone()

                        if row:
                            collection_uuid = row[0]
                            # 删除 embedding 记录
                            conn.execute(
                                text("DELETE FROM langchain_pg_embedding WHERE collection_id = :uuid"),
                                {"uuid": collection_uuid}
                            )
                            # 删除 collection 记录
                            conn.execute(
                                text("DELETE FROM langchain_pg_collection WHERE uuid = :uuid"),
                                {"uuid": collection_uuid}
                            )
                            conn.commit()
                            logger.info(f"Deleted PGVector collection: {coll_name}")
                        else:
                            logger.debug(f"PGVector collection not found: {coll_name}")

                    except Exception as e:
                        logger.warning(f"Failed to delete PGVector collection {coll_name}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete PGVector collections for {collection_name}: {e}")
            return False

    @classmethod
    def clear_instance_cache(cls, dataset_id: int = None):
        """
        清除实例缓存

        Args:
            dataset_id: 指定数据集ID，None 表示清除所有
        """
        if dataset_id is not None:
            collection_name = f"vec_ds_{dataset_id}"
            if collection_name in cls._legacy_instances:
                del cls._legacy_instances[collection_name]
                logger.info(f"Cleared Vanna instance cache: {collection_name}")
            if collection_name in cls._agent_instances:
                del cls._agent_instances[collection_name]
                logger.info(f"Cleared Agent instance cache: {collection_name}")
        else:
            cls._legacy_instances.clear()
            cls._agent_instances.clear()
            logger.info("Cleared all Vanna instance caches")
