from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, inspect
from app.models.metadata import Dataset, TrainingLog
from app.core.config import settings
from app.services.db_inspector import DBInspector
from datetime import datetime, date
from decimal import Decimal
import logging
import re
import asyncio
import pandas as pd
import uuid
import json
import hashlib
from openai import OpenAI as OpenAIClient
import redis
from redis.exceptions import RedisError

# Vanna 2.0 Imports
from vanna.core import Agent, ToolRegistry, ToolContext
from vanna.core.user import User, UserResolver, RequestContext
from vanna.core.llm.models import LlmRequest
from vanna.core.enhancer import DefaultLlmContextEnhancer
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
# Note: For SQL execution in Agent, we might need a Runner. 
# But for training (adding DDL), we just need Memory.

# Standard Vanna Imports for Mixin Pattern
from vanna.legacy.openai import OpenAI_Chat
from vanna.legacy.chromadb import ChromaDB_VectorStore

logger = logging.getLogger(__name__)


# Custom Exception for Training Control
class TrainingStoppedException(Exception):
    """自定义异常：训练被用户中断"""
    pass


class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Legacy Vanna class for SQL generation
    Combines ChromaDB vector store with OpenAI chat
    使用传入的 chroma_client 避免重复创建导致的冲突
    """
    def __init__(self, config=None, chroma_client=None):
        # 如果传入了 chroma_client，直接使用而不调用父类的 __init__
        if chroma_client is not None:
            import chromadb.utils.embedding_functions as embedding_functions
            
            self.chroma_client = chroma_client
            collection_name = config.get('collection_name', 'vanna_collection') if config else 'vanna_collection'
            self.n_results = config.get('n_results', 10) if config else 10
            
            # 初始化 embedding function
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            
            # 创建 vanna 所需的所有 collection
            self.ddl_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_ddl",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self.documentation_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_documentation",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self.sql_collection = self.chroma_client.get_or_create_collection(
                name=f"{collection_name}_sql",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            # 回退到原始初始化方式
            ChromaDB_VectorStore.__init__(self, config=config)
        
        # Initialize with custom OpenAI client
        if config and 'api_base' in config:
            self.client = OpenAIClient(
                api_key=config.get('api_key'),
                base_url=config.get('api_base')
            )
            # Store model name
            self.model = config.get('model', 'gpt-3.5-turbo')
        else:
            OpenAI_Chat.__init__(self, config=config)
    
    def submit_prompt(self, prompt, **kwargs):
        """
        Override submit_prompt to use custom client
        """
        if hasattr(self, 'client'):
            # Extract messages if provided in prompt
            if isinstance(prompt, list):
                messages = prompt
            else:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that generates SQL queries."},
                    {"role": "user", "content": str(prompt)}
                ]
            
            # Ensure all messages have valid content
            validated_messages = []
            for msg in messages:
                if isinstance(msg.get('content'), str) and msg['content'].strip():
                    validated_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
            
            if not validated_messages:
                raise ValueError("No valid messages to send to LLM")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=validated_messages,
                **kwargs
            )
            return response.choices[0].message.content
        else:
            return super().submit_prompt(prompt, **kwargs)


class SimpleUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="admin", email="admin@example.com", group_memberships=['admin'])

class VannaManager:
    # Class-level Redis client for connection reuse
    _redis_client = None
    _redis_available = False
    
    # Class-level ChromaDB client cache to prevent "different settings" error
    _chroma_clients = {}  # {collection_name: vanna_instance}
    _agent_instances = {}  # {collection_name: agent_instance}
    
    # Global ChromaDB persistent client (singleton)
    _global_chroma_client = None
    
    @classmethod
    def _get_redis_client(cls):
        """
        Get or initialize Redis client with connection pooling.
        Returns None if Redis is unavailable (graceful degradation).
        """
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                cls._redis_client.ping()
                cls._redis_available = True
                logger.info(f"Redis connected successfully: {settings.REDIS_URL}")
            except RedisError as e:
                logger.warning(f"Redis connection failed: {e}. Cache disabled.")
                cls._redis_client = None
                cls._redis_available = False
            except Exception as e:
                logger.warning(f"Unexpected error connecting to Redis: {e}. Cache disabled.")
                cls._redis_client = None
                cls._redis_available = False
        
        return cls._redis_client if cls._redis_available else None
    
    @staticmethod
    def _generate_cache_key(dataset_id: int, question: str) -> str:
        """
        Generate cache key for a query.
        Format: bi:cache:{dataset_id}:{hash(question)}
        """
        question_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
        return f"bi:cache:{dataset_id}:{question_hash}"
    
    @staticmethod
    def _generate_sql_cache_key(dataset_id: int, question: str) -> str:
        """
        Generate SQL cache key for a query.
        Format: bi:sql_cache:{dataset_id}:{hash(question)}
        """
        question_hash = hashlib.md5(question.encode('utf-8')).hexdigest()
        return f"bi:sql_cache:{dataset_id}:{question_hash}"
    
    @staticmethod
    def _serialize_cache_data(result: dict) -> str:
        """
        Serialize result data to JSON string for Redis storage.
        """
        return json.dumps(result, ensure_ascii=False)
    
    @staticmethod
    def _deserialize_cache_data(data: str) -> dict:
        """
        Deserialize JSON string from Redis to result dict.
        """
        return json.loads(data)
    
    @classmethod
    def clear_cache(cls, dataset_id: int) -> int:
        """
        Clear all cached queries for a specific dataset.
        Clears both result cache and SQL cache.
        Useful when dataset is retrained or terms are updated.
        
        Args:
            dataset_id: Dataset ID to clear cache for
            
        Returns:
            int: Number of keys deleted, -1 if Redis unavailable
        """
        redis_client = cls._get_redis_client()
        if not redis_client:
            logger.warning("Redis unavailable, cannot clear cache")
            return -1
        
        try:
            total_deleted = 0
            
            # 1. Clear result cache
            result_pattern = f"bi:cache:{dataset_id}:*"
            result_keys = redis_client.keys(result_pattern)
            if result_keys:
                deleted = redis_client.delete(*result_keys)
                total_deleted += deleted
                logger.info(f"Cleared {deleted} result cache entries for dataset {dataset_id}")
            
            # 2. Clear SQL cache
            sql_pattern = f"bi:sql_cache:{dataset_id}:*"
            sql_keys = redis_client.keys(sql_pattern)
            if sql_keys:
                deleted = redis_client.delete(*sql_keys)
                total_deleted += deleted
                logger.info(f"Cleared {deleted} SQL cache entries for dataset {dataset_id}")
            
            if total_deleted > 0:
                logger.info(f"Total cleared {total_deleted} cache entries for dataset {dataset_id}")
            else:
                logger.info(f"No cached entries found for dataset {dataset_id}")
            
            return total_deleted
        except RedisError as e:
            logger.error(f"Failed to clear cache for dataset {dataset_id}: {e}")
            return -1
    
    @staticmethod
    def _get_global_chroma_client():
        """
        获取全局单例ChromaDB客户端，确保所有实例使用相同配置
        """
        if VannaManager._global_chroma_client is None:
            import chromadb
            VannaManager._global_chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
            logger.info(f"Initialized global ChromaDB client at {settings.CHROMA_PERSIST_DIR}")
        return VannaManager._global_chroma_client
    
    @staticmethod
    def get_legacy_vanna(dataset_id: int):
        """
        Initialize and return a Legacy Vanna instance for SQL generation.
        Uses the same configuration as Agent but with Legacy API.
        Reuses existing client if already created to avoid ChromaDB conflicts.
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        # Return cached instance if exists
        if collection_name in VannaManager._chroma_clients:
            logger.debug(f"Reusing existing Vanna instance for collection {collection_name}")
            return VannaManager._chroma_clients[collection_name]
        
        # 获取全局客户端并传入 VannaLegacy，避免内部重复创建
        global_client = VannaManager._get_global_chroma_client()
        
        # Create new instance with shared global client
        vn = VannaLegacy(
            config={
                'api_key': settings.DASHSCOPE_API_KEY,
                'model': settings.QWEN_MODEL,
                'n_results': settings.CHROMA_N_RESULTS,
                'collection_name': collection_name,
                'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1'
            },
            chroma_client=global_client  # 传入全局客户端
        )
        
        # Enable data visibility for LLM to support intermediate_sql reasoning
        vn.allow_llm_to_see_data = True
        
        # Cache the instance
        VannaManager._chroma_clients[collection_name] = vn
        logger.info(f"Created new Vanna instance for collection {collection_name}")
        
        return vn

    @staticmethod
    def get_agent(dataset_id: int):
        """
        Initialize and return a configured Vanna Agent instance (Vanna 2.0).
        Reuses existing agent if already created to avoid ChromaDB conflicts.
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        # Return cached agent if exists
        if collection_name in VannaManager._agent_instances:
            logger.debug(f"Reusing existing Agent instance for collection {collection_name}")
            return VannaManager._agent_instances[collection_name]
        
        # 1. LLM Service (Qwen via OpenAI compatible API)
        llm_service = OpenAILlmService(
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.QWEN_MODEL,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 2. Agent Memory (ChromaDB)
        # ChromaDB配置从.env文件读取
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
        VannaManager._agent_instances[collection_name] = agent
        logger.info(f"Created new Agent instance for collection {collection_name}")
        
        return agent

    @staticmethod
    def train_dataset(dataset_id: int, table_names: list[str], db_session: Session):
        """
        Train the dataset by extracting DDLs and feeding them to Vanna Memory.
        This wrapper handles the sync-to-async bridge.
        """
        # 在训练前主动清理该数据集的缓存，避免 ChromaDB 实例冲突
        collection_name = f"vec_ds_{dataset_id}"
        if collection_name in VannaManager._chroma_clients:
            logger.info(f"Clearing cached Vanna instance before training: {collection_name}")
            del VannaManager._chroma_clients[collection_name]
        if collection_name in VannaManager._agent_instances:
            logger.info(f"Clearing cached Agent instance before training: {collection_name}")
            del VannaManager._agent_instances[collection_name]
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(VannaManager.train_dataset_async(dataset_id, table_names, db_session))

    @staticmethod
    def _checkpoint_and_check_interrupt(db_session: Session, dataset_id: int, progress: int, log_message: str):
        """
        检查点：更新进度、记录日志、检查中断
        
        Args:
            db_session: 数据库会话
            dataset_id: 数据集ID
            progress: 当前进度 (0-100)
            log_message: 日志消息
            
        Raises:
            TrainingStoppedException: 如果状态为 paused
        """
        # 1. 更新进度
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        dataset.process_rate = progress
        
        # 2. 记录日志
        training_log = TrainingLog(
            dataset_id=dataset_id,
            content=f"[{progress}%] {log_message}"
        )
        db_session.add(training_log)
        db_session.commit()
        db_session.refresh(dataset)  # 刷新以获取最新状态
        
        logger.info(f"Checkpoint: Dataset {dataset_id} progress {progress}% - {log_message}")
        
        # 3. 检查是否被中断
        if dataset.status == "paused":
            logger.warning(f"Training interrupted by user for dataset {dataset_id}")
            raise TrainingStoppedException(f"训练被用户中断 (Dataset {dataset_id})")
    
    @staticmethod
    def delete_collection(dataset_id: int):
        """
        删除 Vanna/ChromaDB 中指定 dataset 的 collection
        用于清理向量库数据
        
        Args:
            dataset_id: 数据集ID
            
        Returns:
            bool: 是否成功删除
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        try:
            # 1. 从缓存中移除
            if collection_name in VannaManager._chroma_clients:
                del VannaManager._chroma_clients[collection_name]
                logger.info(f"Removed Vanna instance from cache: {collection_name}")
            
            if collection_name in VannaManager._agent_instances:
                del VannaManager._agent_instances[collection_name]
                logger.info(f"Removed Agent instance from cache: {collection_name}")
            
            # 2. 删除 ChromaDB collection（使用全局客户端）
            chroma_client = VannaManager._get_global_chroma_client()
            
            try:
                chroma_client.delete_collection(name=collection_name)
                logger.info(f"Successfully deleted ChromaDB collection: {collection_name}")
            except Exception as e:
                # Collection 不存在也视为成功
                if "does not exist" in str(e).lower():
                    logger.info(f"Collection {collection_name} does not exist, nothing to delete")
                else:
                    logger.error(f"Failed to delete collection {collection_name}: {e}")
                    raise
            
            # 3. 清理缓存
            VannaManager.clear_cache(dataset_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection for dataset {dataset_id}: {e}")
            return False

    @staticmethod
    def get_training_data(dataset_id: int, page: int = 1, page_size: int = 20, type_filter: str = None) -> dict:
        """
        从 ChromaDB collection 中获取训练数据（QA对、DDL、文档等）
        支持分页查询，兼容旧版和新版存储格式
        
        Args:
            dataset_id: 数据集ID
            page: 页码（从1开始）
            page_size: 每页数量
            type_filter: 类型筛选，可选值: 'ddl', 'sql', 'documentation', None(全部)
            
        Returns:
            dict: {
                'total': int,  # 总数
                'items': [     # 训练数据列表
                    {
                        'id': str,
                        'question': str,
                        'sql': str,
                        'training_data_type': str,  # 'sql', 'ddl', 'documentation'
                        'created_at': str or None
                    }
                ],
                'page': int,
                'page_size': int
            }
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        try:
            # 获取全局 ChromaDB 客户端
            chroma_client = VannaManager._get_global_chroma_client()
            
            all_items = []
            
            # 方案 1：新版分开存储的 collection
            # 根据 type_filter 决定查询哪些 collection
            if type_filter and type_filter != 'all':
                collection_configs = [(f"{collection_name}_{type_filter}", type_filter)]
            else:
                collection_configs = [
                    (f"{collection_name}_ddl", 'ddl'),
                    (f"{collection_name}_documentation", 'documentation'),
                    (f"{collection_name}_sql", 'sql'),
                ]
            
            for coll_name, data_type in collection_configs:
                try:
                    collection = chroma_client.get_collection(name=coll_name)
                    result = collection.get(include=['documents', 'metadatas'])
                    
                    ids = result.get('ids', [])
                    documents = result.get('documents', [])
                    metadatas = result.get('metadatas', [])
                    
                    for i, doc_id in enumerate(ids):
                        document = documents[i] if i < len(documents) else ''
                        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
                        
                        # 处理 metadata 中的 question（可能是 JSON 字符串）
                        question = metadata.get('question', '')
                        if isinstance(question, str) and question.startswith('{'):
                            try:
                                import json
                                parsed = json.loads(question)
                                question = parsed.get('question', '')
                            except:
                                pass
                        
                        # 处理 document（sql 可能在 document 或 metadata 中）
                        sql = document
                        if isinstance(sql, str) and sql.startswith('{'):
                            try:
                                import json
                                parsed = json.loads(sql)
                                question = parsed.get('question', question)
                                sql = parsed.get('sql', sql)
                            except:
                                pass
                        
                        training_data_type = data_type
                        
                        # DDL 类型：使用表名作为 question
                        if training_data_type == 'ddl' and not question:
                            import re
                            table_match = re.search(r'CREATE TABLE\s+`?(\w+)`?', sql, re.IGNORECASE)
                            if table_match:
                                question = table_match.group(1)
                            else:
                                question = "数据库表结构定义"
                        
                        # 文档类型
                        if training_data_type == 'documentation' and not question:
                            if '业务术语' in sql:
                                # 提取术语名称
                                term_match = re.search(r'业务术语[：:]\s*(.+?)\n', sql)
                                if term_match:
                                    question = term_match.group(1)
                                else:
                                    question = "业务术语定义"
                            elif 'joined with' in sql.lower():
                                # 提取表关系
                                relation_match = re.search(r'`(\w+)`.*?joined with.*?`(\w+)`', sql, re.IGNORECASE)
                                if relation_match:
                                    question = f"{relation_match.group(1)} 与 {relation_match.group(2)} 的关系"
                                else:
                                    question = "表关系描述"
                            else:
                                # 取文档前50字符作为描述
                                question = sql[:50].strip()
                        
                        # SQL QA 对
                        if training_data_type == 'sql' and not question:
                            question = metadata.get('text', '示例查询')
                        
                        all_items.append({
                            'id': doc_id,
                            'question': question or '未命名',
                            'sql': sql,
                            'training_data_type': training_data_type,
                            'created_at': metadata.get('created_at') or metadata.get('timestamp')
                        })
                        
                except Exception as e:
                    if "does not exist" not in str(e).lower():
                        logger.warning(f"Failed to get data from collection {coll_name}: {e}")
                    continue
            
            # 方案 2：旧版单一 collection 格式（兼容旧数据）
            if len(all_items) == 0:
                try:
                    collection = chroma_client.get_collection(name=collection_name)
                    result = collection.get(include=['documents', 'metadatas'])
                    
                    ids = result.get('ids', [])
                    documents = result.get('documents', [])
                    metadatas = result.get('metadatas', [])
                    
                    for i, doc_id in enumerate(ids):
                        document = documents[i] if i < len(documents) else ''
                        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
                        
                        question = metadata.get('question', '')
                        sql = document
                        
                        # 自动检测数据类型
                        training_data_type = 'sql'  # 默认
                        if 'CREATE TABLE' in document.upper() or 'CREATE VIEW' in document.upper():
                            training_data_type = 'ddl'
                        elif question is None or question == '':
                            if '业务' in document or 'joined with' in document.lower():
                                training_data_type = 'documentation'
                        
                        # 应用类型筛选
                        if type_filter and type_filter != 'all' and training_data_type != type_filter:
                            continue
                        
                        # DDL 类型：使用表名作为 question
                        if training_data_type == 'ddl' and not question:
                            import re
                            table_match = re.search(r'CREATE TABLE\s+`?(\w+)`?', sql, re.IGNORECASE)
                            if table_match:
                                question = f"表结构: {table_match.group(1)}"
                            else:
                                question = "数据库表结构定义"
                        
                        # 文档类型
                        if training_data_type == 'documentation' and not question:
                            question = "业务文档"
                        
                        # SQL QA 对
                        if training_data_type == 'sql' and not question:
                            question = metadata.get('text', '示例查询')
                        
                        all_items.append({
                            'id': doc_id,
                            'question': question,
                            'sql': sql,
                            'training_data_type': training_data_type,
                            'created_at': metadata.get('created_at') or metadata.get('timestamp')
                        })
                        
                except Exception as e:
                    if "does not exist" not in str(e).lower():
                        logger.warning(f"Failed to get data from legacy collection {collection_name}: {e}")
            
            # 计算分页
            total = len(all_items)
            start = (page - 1) * page_size
            end = start + page_size
            items = all_items[start:end]
            
            logger.info(f"Retrieved {len(items)} training data items (page {page}/{(total + page_size - 1) // page_size if total > 0 else 1}) for dataset {dataset_id}")
            
            return {
                'total': total,
                'items': items,
                'page': page,
                'page_size': page_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get training data for dataset {dataset_id}: {e}")
            raise ValueError(f"获取训练数据失败: {str(e)}")

    @staticmethod
    async def train_dataset_async(dataset_id: int, table_names: list[str], db_session: Session):
        """
        异步训练数据集，支持进度更新和中断控制
        
        流程：
        - Step 0-10%: 初始化、检查数据库连接、提取 DDL
        - Step 10-40%: 训练 DDL 到 Vanna
        - Step 40-80%: 训练文档/业务术语
        - Step 80-100%: 生成示例 SQLQA 对并训练
        
        Args:
            dataset_id: 数据集ID
            table_names: 要训练的表名列表
            db_session: 数据库会话
        """
        logger.info(f"Starting training for dataset {dataset_id} with tables: {table_names}")
        
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.error(f"Dataset {dataset_id} not found")
            return
        
        try:
            # === Step 0: 初始化 (0%) ===
            dataset.status = "training"
            dataset.process_rate = 0
            dataset.error_msg = None
            db_session.commit()
            
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 0, "训练启动")
            
            # === Step 1: 检查数据库连接和提取 DDL (0-10%) ===
            datasource = dataset.datasource
            if not datasource:
                raise ValueError("DataSource associated with dataset not found")
            
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 5, "检查数据源连接")
            
            # 提取 DDLs
            ddls = []
            for i, table_name in enumerate(table_names):
                try:
                    ddl = DBInspector.get_table_ddl(datasource, table_name)
                    ddls.append((table_name, ddl))
                    
                    # 每处理一个表，更新一次进度
                    progress = 5 + int((i + 1) / len(table_names) * 5)
                    VannaManager._checkpoint_and_check_interrupt(
                        db_session, dataset_id, progress, 
                        f"提取表 DDL: {table_name} ({i+1}/{len(table_names)})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to get DDL for {table_name}: {e}")
                    # 继续处理其他表
            
            if not ddls:
                raise ValueError("没有成功提取任何表的 DDL")
            
            # === Step 2: 初始化 Vanna 实例 (10%) ===
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 10, "初始化 Vanna 实例")
            
            # 使用 Legacy API 进行训练
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # === Step 3: 训练 DDL (10-40%) ===
            for i, (table_name, ddl) in enumerate(ddls):
                if ddl:
                    vn.train(ddl=ddl)
                    
                    # 更新进度
                    progress = 10 + int((i + 1) / len(ddls) * 30)
                    VannaManager._checkpoint_and_check_interrupt(
                        db_session, dataset_id, progress,
                        f"训练 DDL: {table_name} ({i+1}/{len(ddls)})"
                    )
            
            # === Step 4: 训练文档/业务术语 (40-80%) ===
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 40, "开始训练业务术语")
            
            # 获取并训练业务术语
            from app.models.metadata import BusinessTerm
            business_terms = db_session.query(BusinessTerm).filter(
                BusinessTerm.dataset_id == dataset_id
            ).all()
            
            if business_terms:
                for i, term in enumerate(business_terms):
                    doc_content = f"业务术语: {term.term}\n定义: {term.definition}"
                    vn.train(documentation=doc_content)
                    
                    progress = 40 + int((i + 1) / len(business_terms) * 20)
                    VannaManager._checkpoint_and_check_interrupt(
                        db_session, dataset_id, progress,
                        f"训练业务术语: {term.term} ({i+1}/{len(business_terms)})"
                    )
            else:
                VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 60, "无业务术语，跳过")
            
            # 训练表关系文档
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 70, "生成表关系文档")
            
            # 生成表关系描述
            table_relationships_doc = f"""数据库表结构：
本数据集包含以下表：{', '.join([name for name, _ in ddls])}

请根据表名和字段名生成 SQL 查询。
"""
            vn.train(documentation=table_relationships_doc)
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 80, "表关系文档训练完成")
            
            # === Step 5: 生成示例 SQLQA 对 (80-100%) ===
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 85, "生成示例 SQL 查询")
            
            # 为主要表生成基本查询示例
            example_queries = []
            for table_name, _ in ddls[:3]:  # 只为前3个表生成示例
                example_queries.append((
                    f"查询 {table_name} 表的所有数据",
                    f"SELECT * FROM {table_name} LIMIT 100"
                ))
                example_queries.append((
                    f"统计 {table_name} 表的总数",
                    f"SELECT COUNT(*) as total FROM {table_name}"
                ))
            
            for i, (question, sql) in enumerate(example_queries):
                vn.train(question=question, sql=sql)
                
                progress = 85 + int((i + 1) / len(example_queries) * 15)
                VannaManager._checkpoint_and_check_interrupt(
                    db_session, dataset_id, progress,
                    f"训练示例查询 ({i+1}/{len(example_queries)})"
                )
            
            # === 完成 (100%) ===
            dataset.status = "completed"
            dataset.process_rate = 100
            dataset.last_train_at = datetime.utcnow()
            db_session.commit()
            
            VannaManager._checkpoint_and_check_interrupt(db_session, dataset_id, 100, "训练完成")
            
            logger.info(f"Training completed successfully for dataset {dataset_id}")
            
            # 清理缓存
            cleared = VannaManager.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training dataset {dataset_id}")
            
        except TrainingStoppedException as e:
            # 被用户中断
            logger.warning(f"Training stopped by user for dataset {dataset_id}: {e}")
            dataset.error_msg = str(e)
            db_session.commit()
            
            # 记录中断日志
            training_log = TrainingLog(
                dataset_id=dataset_id,
                content=f"[{dataset.process_rate}%] 训练被用户中断"
            )
            db_session.add(training_log)
            db_session.commit()
            
        except Exception as e:
            # 训练失败
            logger.error(f"Training failed for dataset {dataset_id}: {e}", exc_info=True)
            dataset.status = "failed"
            dataset.error_msg = str(e)
            db_session.commit()
            
            # 记录错误日志
            training_log = TrainingLog(
                dataset_id=dataset_id,
                content=f"[{dataset.process_rate}%] 训练失败: {str(e)[:200]}"
            )
            db_session.add(training_log)
            db_session.commit()

    @staticmethod
    def train_term(dataset_id: int, term: str, definition: str, db_session: Session):
        """
        Train a business term by adding it to Vanna's documentation memory.
        Uses Legacy API for consistency with existing training approach.
        Clears cache after training to ensure fresh results.
        """
        try:
            # Get Legacy Vanna instance
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # Format as documentation and train
            doc_content = f"业务术语: {term}\n定义: {definition}"
            vn.train(documentation=doc_content)
            
            logger.info(f"Successfully trained business term '{term}' for dataset {dataset_id}")
            
            # Clear cache after training new term
            cleared = VannaManager.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training term '{term}'")
            
        except Exception as e:
            logger.error(f"Failed to train business term '{term}': {e}")
            raise ValueError(f"训练问答对失败: {str(e)}")
    
    @staticmethod
    def train_relationships(dataset_id: int, relationships: list[str], db_session: Session):
        """
        Train table relationships by adding them to Vanna's documentation memory.
        This enhances Vanna's ability to generate correct JOIN queries.
        
        Args:
            dataset_id: Dataset ID
            relationships: List of relationship descriptions (natural language)
            db_session: Database session
            
        Example relationships:
            [
                "The table `users` can be joined with table `orders` on the condition `users`.`id` = `orders`.`user_id`.",
                "The table `orders` can be joined with table `products` on the condition `orders`.`product_id` = `products`.`id`."
            ]
        """
        if not relationships or len(relationships) == 0:
            logger.info(f"No relationships to train for dataset {dataset_id}")
            return
        
        try:
            # Get Legacy Vanna instance
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            logger.info(f"Training {len(relationships)} relationships for dataset {dataset_id}")
            
            # Train each relationship as documentation
            for i, rel_desc in enumerate(relationships, 1):
                # Format as documentation
                doc_content = f"表关系: {rel_desc}"
                vn.train(documentation=doc_content)
                logger.debug(f"Trained relationship {i}/{len(relationships)}: {rel_desc[:80]}...")
            
            logger.info(f"Successfully trained {len(relationships)} relationships for dataset {dataset_id}")
            
            # Clear cache after training relationships
            cleared = VannaManager.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training relationships")
            
        except Exception as e:
            logger.error(f"Failed to train relationships: {e}")
            raise ValueError(f"训练表关系失败: {str(e)}")
    
    @staticmethod
    def train_qa(dataset_id: int, question: str, sql: str, db_session: Session):
        """
        Train a successful question-SQL pair from user feedback.
        This helps AI learn from correct examples and improve future responses.
        
        Args:
            dataset_id: Dataset ID
            question: User's question
            sql: Correct SQL for the question
            db_session: Database session
        
        Raises:
            ValueError: If training fails
        """
        try:
            # Get Legacy Vanna instance
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # Train the Q-SQL pair
            vn.train(question=question, sql=sql)
            
            logger.info(f"Successfully trained Q-A pair for dataset {dataset_id}: '{question[:50]}...'")
            
            # Clear cache after training to ensure fresh results
            cleared = VannaManager.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training Q-A pair")
            
        except Exception as e:
            logger.error(f"Failed to train Q-A pair for dataset {dataset_id}: {e}")
            raise ValueError(f"训练问答对失败: {str(e)}")

    @staticmethod
    async def generate_result(dataset_id: int, question: str, db_session: Session, allow_cache: bool = True):
        """
        Generate SQL and execute it with intelligent multi-round dialogue (Auto-Reflection Loop).
        Now with Redis-based query caching for improved performance.
        
        Features:
        1. Redis-based query caching with configurable TTL
        2. LLM-driven intermediate SQL detection and execution
        3. Intelligent clarification generation when ambiguous
        4. Graceful text-only responses (no exceptions for non-SQL)
        5. LLM-powered friendly error messages on failures
        6. All responses in Chinese
        
        Args:
            dataset_id: Dataset ID
            question: User's question
            db_session: Database session
            allow_cache: Whether to use cache (default: True)
            
        Returns:
            dict: Result with sql, columns, rows, chart_type, etc.
                  Includes 'from_cache' flag when result is from cache
        """
        execution_steps = []
        
        # === Step 0: SQL Cache Check (v1.3 性能优化) ===
        if allow_cache:
            redis_client = VannaManager._get_redis_client()
            sql_cache_key = VannaManager._generate_sql_cache_key(dataset_id, question)
            
            if redis_client:
                try:
                    cached_sql = redis_client.get(sql_cache_key)
                    if cached_sql:
                        logger.info(f"SQL cache hit for dataset {dataset_id}, question: {question[:50]}...")
                        execution_steps.append("SQL缓存命中")
                        
                        # 关键点：拿到缓存的 SQL 后，重新执行查询获取最新数据
                        try:
                            # 获取 dataset 和 datasource
                            stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
                            result = db_session.execute(stmt)
                            dataset = result.scalars().first()
                            
                            if not dataset or not dataset.datasource:
                                # 如果 dataset 或 datasource 不存在，这个缓存已经无效了
                                logger.warning(f"Dataset {dataset_id} or datasource not found, invalidating SQL cache")
                                redis_client.delete(sql_cache_key)
                                execution_steps.append("缓存已失效，进入常规流程")
                            else:
                                # 重新执行 SQL 查询
                                engine = DBInspector.get_engine(dataset.datasource)
                                df = pd.read_sql(cached_sql, engine)
                                execution_steps.append(f"SQL缓存命中，重新执行查询，返回 {len(df)} 行")
                                
                                # 推断图表类型
                                chart_type = VannaManager._infer_chart_type(df)
                                
                                # 序列化数据
                                cleaned_rows = VannaManager._serialize_dataframe(df)
                                
                                return {
                                    "sql": cached_sql,
                                    "columns": df.columns.tolist(),
                                    "rows": cleaned_rows,
                                    "chart_type": chart_type,
                                    "summary": None,
                                    "steps": execution_steps,
                                    "from_cache": True,
                                    "cache_type": "sql"  # 标记是 SQL 级缓存
                                }
                        except Exception as e:
                            logger.warning(f"Cached SQL execution failed: {e}. Proceeding with full generation.")
                            execution_steps.append(f"缓存 SQL 执行失败: {str(e)[:50]}，进入常规流程")
                            # 删除无效缓存
                            redis_client.delete(sql_cache_key)
                    else:
                        logger.debug(f"SQL cache miss for dataset {dataset_id}")
                        execution_steps.append("SQL缓存未命中")
                except RedisError as e:
                    logger.warning(f"SQL cache read failed: {e}. Proceeding without cache.")
                    execution_steps.append(f"SQL缓存读取失败: {str(e)[:50]}")
        
        # === Step 1: 原有结果缓存检查 (保留兼容性) ===
        # 注意：这里的结果缓存会缓存完整的查询结果，而 SQL 缓存只缓存 SQL
        # 两种缓存可以共存，结果缓存 TTL 更短（5分钟），SQL 缓存 TTL 更长（7天）
        if allow_cache:
            redis_client = VannaManager._get_redis_client()
            cache_key = VannaManager._generate_cache_key(dataset_id, question)
            
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        logger.info(f"Cache hit for dataset {dataset_id}, question: {question[:50]}...")
                        result = VannaManager._deserialize_cache_data(cached_data)
                        result['from_cache'] = True
                        # 不要累加 steps，直接替换为缓存标记
                        result['steps'] = ["从缓存返回结果"]
                        return result
                    else:
                        logger.debug(f"Cache miss for dataset {dataset_id}")
                        execution_steps.append("缓存未命中")
                except RedisError as e:
                    logger.warning(f"Cache read failed: {e}. Proceeding without cache.")
                    execution_steps.append(f"缓存读取失败: {str(e)[:50]}")
        
        try:
            # === Step A: Initial Setup ===
            # 1. Get Dataset with eager loading of datasource
            stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
            result = db_session.execute(stmt)
            dataset = result.scalars().first()
            
            if not dataset:
                return {
                    "sql": None,
                    "columns": None,
                    "rows": None,
                    "chart_type": "clarification",
                    "answer_text": f"找不到数据集 ID: {dataset_id}，请检查数据集是否存在。",
                    "steps": ["数据集查找失败"]
                }
            
            if not dataset.datasource:
                return {
                    "sql": None,
                    "columns": None,
                    "rows": None,
                    "chart_type": "clarification",
                    "answer_text": "数据集未关联数据源，请先配置数据源。",
                    "steps": ["数据源配置检查失败"]
                }

            # 2. Get Vanna instance and database engine
            vn = VannaManager.get_legacy_vanna(dataset_id)
            engine = DBInspector.get_engine(dataset.datasource)
            
            execution_steps.append("初始化完成")

            # === Step B: Initial Generation ===
            try:
                llm_response = vn.generate_sql(question + " (请用中文回答)")
                execution_steps.append("LLM 初始响应生成")
                logger.info(f"Initial LLM response: {llm_response}")
            except Exception as e:
                logger.error(f"Initial SQL generation failed: {e}")
                # Use LLM to generate friendly error message
                try:
                    error_prompt = f"""系统在尝试生成 SQL 时报错了: {str(e)}
请用中文礼貌地告诉用户查询出错了，并建议他们换一种问法或提供更多细节。
保持简洁友好，不要提及技术细节。"""
                    friendly_msg = vn.submit_prompt(error_prompt)
                    execution_steps.append("LLM 生成友好错误消息")
                except:
                    friendly_msg = "抱歉，我在理解您的问题时遇到了困难。能否请您换一种方式描述，或者提供更多相关信息？"
                
                return {
                    "sql": None,
                    "columns": None,
                    "rows": None,
                    "chart_type": "clarification",
                    "answer_text": friendly_msg,
                    "steps": execution_steps
                }

            # === Step C: Intelligent Processing Loop ===
            # Process the response iteratively (max 3 rounds to prevent infinite loops)
            max_rounds = 3
            current_response = llm_response
            
            for round_num in range(1, max_rounds + 1):
                execution_steps.append(f"第 {round_num} 轮处理")
                logger.info(f"Round {round_num}: Processing response")
                
                # === Situation 1: Intermediate SQL ===
                intermediate_sql = VannaManager._extract_intermediate_sql(current_response)
                
                if intermediate_sql:
                    execution_steps.append(f"检测到中间 SQL: {intermediate_sql[:100]}")
                    logger.info(f"Detected intermediate SQL: {intermediate_sql}")
                    
                    try:
                        # Execute intermediate SQL
                        df_intermediate = pd.read_sql(intermediate_sql, engine)
                        execution_steps.append(f"中间 SQL 执行成功，获取 {len(df_intermediate)} 行")
                        
                        # Extract distinct values
                        values = []
                        if not df_intermediate.empty:
                            values = df_intermediate.iloc[:, 0].tolist()
                            values = [str(v) for v in values if v is not None]
                        
                        logger.info(f"Intermediate values: {values}")
                        execution_steps.append(f"中间值: {values}")
                        
                        # LLM second-round reasoning
                        reflection_prompt = f"""用户的问题是: {question}

我执行了中间查询，数据库中存在的相关值为: {values}

请根据这些值:
1. 如果能确定用户意图，请生成最终 SQL 查询(只输出 SQL，不要解释)。
2. 如果不能确定(例如用户问'大客户'但数据库只有'VIP'和'普通')，请用**中文**生成一个澄清问题，询问用户指的是哪一个值。

请直接输出 SQL 或澄清问题，不要额外解释。"""
                        
                        execution_steps.append("LLM 二次推理")
                        current_response = vn.submit_prompt(reflection_prompt)
                        logger.info(f"LLM reflection response: {current_response}")
                        
                        # Continue to next iteration to process the new response
                        continue
                        
                    except Exception as e:
                        logger.warning(f"Intermediate SQL execution failed: {e}")
                        execution_steps.append(f"中间 SQL 执行失败: {str(e)[:100]}")
                        # Continue with current response, might be clarification
                
                # === Situation 2: Pure Text (Clarification/Refusal) ===
                # Check if response is valid SQL
                try:
                    cleaned_sql = VannaManager._clean_sql(current_response)
                    is_sql = VannaManager._is_valid_sql(cleaned_sql)
                except:
                    is_sql = False
                    cleaned_sql = ""
                
                if not is_sql:
                    # It's pure text - treat as clarification
                    execution_steps.append("LLM 返回纯文本(澄清/说明)")
                    logger.info(f"Pure text response: {current_response}")
                    
                    return {
                        "sql": None,
                        "columns": None,
                        "rows": None,
                        "chart_type": "clarification",
                        "answer_text": current_response,
                        "steps": execution_steps
                    }
                
                # === Situation 3: Valid SQL ===
                execution_steps.append("检测到有效 SQL")
                
                # 添加LIMIT子句防止查询过多数据导致超时
                # 判断 SQL 是否已有 LIMIT 子句
                sql_upper = cleaned_sql.upper()
                has_limit = 'LIMIT' in sql_upper
                
                if not has_limit:
                    # 在SQL末尾添加LIMIT
                    cleaned_sql = cleaned_sql.rstrip(';').strip() + ' LIMIT 1000'
                    execution_steps.append("自动添加 LIMIT 1000 防止过多数据")
                elif has_limit:
                    # 检查 LIMIT 值是否过大，如果超过 5000 则替换为 1000
                    import re
                    limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
                    if limit_match:
                        limit_value = int(limit_match.group(1))
                        if limit_value > 5000:
                            # 替换为更小的值
                            cleaned_sql = re.sub(r'LIMIT\s+\d+', 'LIMIT 1000', cleaned_sql, flags=re.IGNORECASE)
                            execution_steps.append(f"将 LIMIT {limit_value} 调整为 LIMIT 1000 防止超时")
                
                try:
                    # Execute the SQL with timeout protection
                    df = pd.read_sql(cleaned_sql, engine)
                    execution_steps.append(f"SQL 执行成功，返回 {len(df)} 行")
                    logger.info(f"SQL executed successfully: {len(df)} rows")
                    
                    # Chart Type Inference
                    chart_type = VannaManager._infer_chart_type(df)
                    execution_steps.append(f"推断图表类型: {chart_type}")
                    
                    # Serialize data
                    cleaned_rows = VannaManager._serialize_dataframe(df)
                    
                    # Generate Business Insight (Analyst Agent)
                    insight = None
                    if len(df) > 0:  # 只有数据不为空时才生成分析
                        try:
                            execution_steps.append("正在生成业务分析...")
                            insight = VannaManager.generate_data_insight(
                                question=question,
                                sql=cleaned_sql,
                                df=df,
                                dataset_id=dataset_id
                            )
                            execution_steps.append("业务分析生成完成")
                            logger.info(f"Business insight generated: {insight[:50]}...")
                        except Exception as insight_error:
                            logger.warning(f"Failed to generate insight: {insight_error}")
                            execution_steps.append("业务分析生成失败")
                            insight = None
                    
                    # Prepare result
                    result = {
                        "sql": cleaned_sql,
                        "columns": df.columns.tolist(),
                        "rows": cleaned_rows,
                        "chart_type": chart_type,
                        "summary": None,
                        "steps": execution_steps,
                        "from_cache": False,
                        "insight": insight  # 新增分析师 Agent 的输出
                    }
                    
                    # === Step D: Write to Cache ===
                    if allow_cache:
                        redis_client = VannaManager._get_redis_client()
                        if redis_client:
                            # 1. 写入 SQL 缓存 (v1.3 性能优化 - 保存 SQL，7天 TTL)
                            try:
                                sql_cache_key = VannaManager._generate_sql_cache_key(dataset_id, question)
                                redis_client.setex(
                                    sql_cache_key,
                                    settings.SQL_CACHE_TTL,
                                    cleaned_sql  # 直接存储 SQL 字符串
                                )
                                logger.info(f"SQL cached for dataset {dataset_id}, TTL: {settings.SQL_CACHE_TTL}s (7 days)")
                                execution_steps.append(f"SQL已缓存 (TTL: {settings.SQL_CACHE_TTL}s)")
                            except RedisError as e:
                                logger.warning(f"SQL cache write failed: {e}.")
                                execution_steps.append(f"SQL缓存写入失败: {str(e)[:50]}")
                            
                            # 2. 写入结果缓存 (原有逻辑，保留兼容性，5分钟 TTL)
                            try:
                                cache_key = VannaManager._generate_cache_key(dataset_id, question)
                                cache_data = VannaManager._serialize_cache_data(result)
                                redis_client.setex(
                                    cache_key,
                                    settings.REDIS_CACHE_TTL,
                                    cache_data
                                )
                                logger.info(f"Result cached for dataset {dataset_id}, TTL: {settings.REDIS_CACHE_TTL}s")
                                execution_steps.append(f"结果已缓存 (TTL: {settings.REDIS_CACHE_TTL}s)")
                            except RedisError as e:
                                logger.warning(f"Result cache write failed: {e}. Result returned without caching.")
                                execution_steps.append(f"结果缓存写入失败: {str(e)[:50]}")
                    
                    return result
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"SQL execution failed: {error_msg}")
                    execution_steps.append(f"SQL 执行失败: {error_msg[:100]}")
                    
                    # 检查是否是连接超时错误
                    is_timeout_error = '2013' in error_msg or 'Lost connection' in error_msg or 'timeout' in error_msg.lower()
                    
                    # 如果是超时错误，直接返回友好提示，不再重试
                    if is_timeout_error:
                        error_prompt = f"""查询执行超时了。用户的问题是: {question}

请用中文礼貌地告诉用户：
1. 查询耗时过长，可能是数据量较大
2. 建议缩小时间范围，比如改为“最近 7 天”或“本周”
3. 或者添加更具体的筛选条件

保持简洁友好，不要提及技术细节。"""
                        try:
                            friendly_msg = vn.submit_prompt(error_prompt)
                            execution_steps.append("检测到超时，生成优化建议")
                        except:
                            friendly_msg = "抱歉，查询耗时过长。建议您缩小时间范围（比如改为‘最近 7 天’或‘本周’），或者添加更具体的筛选条件。"
                        
                        return {
                            "sql": cleaned_sql,
                            "columns": None,
                            "rows": None,
                            "chart_type": "clarification",
                            "answer_text": friendly_msg,
                            "steps": execution_steps
                        }
                    
                    # If not the last round, try SQL correction with LLM
                    if round_num < max_rounds:
                        try:
                            execution_steps.append("尝试 LLM 修正 SQL")
                            
                            db_type = dataset.datasource.type.upper()
                            correction_prompt = f"""以下 SQL 在 {db_type} 数据库上执行失败:

SQL:
{cleaned_sql}

错误:
{error_msg}

请分析并修正这个 SQL，使其能正确执行。如果无法修正，请用中文说明原因。
只输出修正后的 SQL 或说明，不要额外解释。"""
                            
                            current_response = vn.submit_prompt(correction_prompt)
                            logger.info(f"LLM correction response: {current_response}")
                            execution_steps.append("LLM 已生成修正方案")
                            
                            # Continue to next iteration
                            continue
                            
                        except Exception as correction_error:
                            logger.error(f"SQL correction failed: {correction_error}")
                            execution_steps.append(f"修正过程出错: {str(correction_error)[:100]}")
                    
                    # Last round or correction failed - use LLM for friendly error
                    try:
                        error_prompt = f"""SQL 查询执行失败，错误信息: {error_msg}
用户的问题是: {question}

请用中文礼貌地告诉用户查询出错了，并建议他们:
1. 检查问题描述是否清晰
2. 或者换一种问法
3. 或者提供更多背景信息

保持简洁友好，不要提及技术细节。"""
                        friendly_msg = vn.submit_prompt(error_prompt)
                        execution_steps.append("LLM 生成友好错误消息")
                    except:
                        friendly_msg = f"抱歉，查询执行遇到了问题。建议您换一种方式描述问题，或者提供更多相关信息。"
                    
                    return {
                        "sql": cleaned_sql,
                        "columns": None,
                        "rows": None,
                        "chart_type": "clarification",
                        "answer_text": friendly_msg,
                        "steps": execution_steps
                    }
            
            # Reached max rounds without success
            execution_steps.append(f"达到最大轮次 ({max_rounds})")
            return {
                "sql": None,
                "columns": None,
                "rows": None,
                "chart_type": "clarification",
                "answer_text": "抱歉，经过多轮分析后仍无法准确理解您的问题。能否请您提供更详细的描述或换一个问法？",
                "steps": execution_steps
            }
        
        except Exception as e:
            # === Situation 4: Global Exception (Fallback) ===
            logger.error(f"Unexpected error in generate_result: {e}", exc_info=True)
            execution_steps.append(f"全局异常: {str(e)[:100]}")
            
            # Try to use LLM for friendly error message
            try:
                vn = VannaManager.get_legacy_vanna(dataset_id)
                error_prompt = f"""系统报错了: {str(e)}
请用中文礼貌地告诉用户查询出错了，并建议他们换一种问法。
保持简洁友好，不要提及技术细节。"""
                friendly_msg = vn.submit_prompt(error_prompt)
                execution_steps.append("LLM 生成异常友好消息")
            except:
                friendly_msg = "抱歉，系统遇到了意外错误。请稍后重试或换一种方式描述您的问题。"
            
            return {
                "sql": None,
                "columns": None,
                "rows": None,
                "chart_type": "clarification",
                "answer_text": friendly_msg,
                "steps": execution_steps
            }

    @staticmethod
    def _infer_chart_type(df: pd.DataFrame) -> str:
        """
        Infer the most suitable chart type based on DataFrame structure.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            str: Chart type ('line', 'bar', 'pie', or 'table')
        """
        if df is None or df.empty:
            return "table"
        
        # Get column types
        lower_cols = [str(c).lower() for c in df.columns]
        has_date = any(x in c for c in lower_cols for x in ['date', 'time', 'year', 'month', 'day'])
        
        # Check data types
        dtypes = df.dtypes.values
        has_num = any(pd.api.types.is_numeric_dtype(t) for t in dtypes)
        has_str = any(pd.api.types.is_string_dtype(t) or pd.api.types.is_object_dtype(t) or pd.api.types.is_datetime64_any_dtype(t) for t in dtypes)
        
        # Decision logic
        if len(df.columns) == 2 and has_date:
            return "line"
        elif len(df.columns) == 2 and has_num and has_str:
            # Could be pie chart if reasonable number of categories
            if len(df) <= 10:
                return "pie"
            return "bar"
        elif len(df.columns) >= 2 and has_num and has_str:
            return "bar"
        else:
            return "table"
    
    @staticmethod
    def _serialize_dataframe(df: pd.DataFrame) -> list:
        """
        Serialize DataFrame to JSON-compatible format.
        
        Args:
            df: DataFrame to serialize
            
        Returns:
            list: List of dictionaries with serialized values
        """
        def serialize(obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        rows = df.to_dict(orient='records')
        cleaned_rows = []
        for row in rows:
            new_row = {k: serialize(v) for k, v in row.items()}
            cleaned_rows.append(new_row)
        
        return cleaned_rows

    @staticmethod
    def _remove_intermediate_marker(response: str) -> str:
        """
        Remove 'intermediate_sql' marker from LLM response.
        
        Args:
            response: Raw LLM response that may contain 'intermediate_sql' marker
            
        Returns:
            str: Cleaned response with marker removed
        """
        if not response or not isinstance(response, str):
            return response
        
        # Remove 'intermediate_sql' marker (case insensitive)
        # Pattern: intermediate_sql\n or intermediate sql\n or intermediate_sql:
        cleaned = re.sub(r'intermediate[_\s]?sql[:\s]*\n?', '', response, flags=re.IGNORECASE)
        
        return cleaned.strip()

    @staticmethod
    def _is_valid_sql(sql: str) -> bool:
        """
        Check if the string is a valid SQL query.
        
        Args:
            sql: String to validate
            
        Returns:
            bool: True if valid SQL, False otherwise
        """
        if not sql or not isinstance(sql, str):
            return False
        
        sql_upper = sql.upper().strip()
        
        # Must contain SELECT and FROM
        # Simple validation - just check for basic SQL structure
        has_select = 'SELECT' in sql_upper
        has_from = 'FROM' in sql_upper
        
        # Check it's not just text with these words
        # Valid SQL should have SELECT near the beginning
        if has_select and has_from:
            select_pos = sql_upper.find('SELECT')
            # SELECT should be within first 50 characters (allowing for comments/whitespace)
            if select_pos < 50:
                return True
        
        return False

    @staticmethod
    def _ensure_clean_sql(sql: str) -> str:
        """
        Ensure SQL is completely clean before execution.
        Removes all markdown, intermediate markers, and extra whitespace.
        
        Args:
            sql: SQL string to clean
            
        Returns:
            str: Cleaned SQL ready for execution
        """
        if not sql or not isinstance(sql, str):
            return sql
        
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove intermediate_sql marker if somehow still present
        sql = re.sub(r'intermediate[_\s]?sql[:\s]*', '', sql, flags=re.IGNORECASE)
        
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        # Remove multiple spaces
        sql = re.sub(r'\s+', ' ', sql)
        
        return sql

    @staticmethod
    def _extract_intermediate_sql(response: str) -> str:
        """
        Extract intermediate SQL from LLM response.
        
        Vanna 2.0 may return intermediate SQL when it needs more context.
        This detects patterns like:
        - Response contains 'intermediate' keyword
        - Response contains SQL but also contains questions or uncertainties
        - Response starts with SELECT but contains reasoning text
        
        Returns:
            str: The intermediate SQL if detected, empty string otherwise
        """
        if not response or not isinstance(response, str):
            return ""
        
        response_lower = response.lower()
        
        # Pattern 1: Explicit intermediate_sql marker
        if 'intermediate_sql' in response_lower or 'intermediate sql' in response_lower:
            # Try to extract SQL after the marker
            sql_start = response.find('SELECT')
            if sql_start == -1:
                sql_start = response.find('select')
            
            if sql_start >= 0:
                # Extract until we hit a double newline or end of string
                sql_end = response.find('\n\n', sql_start)
                if sql_end > 0:
                    intermediate_sql = response[sql_start:sql_end].strip()
                else:
                    intermediate_sql = response[sql_start:].strip()
                
                # Clean up
                intermediate_sql = VannaManager._clean_sql(intermediate_sql)
                if 'SELECT' in intermediate_sql.upper():
                    return intermediate_sql
        
        # Pattern 2: Response contains questions/uncertainties AND SQL
        uncertainty_keywords = ['不确定', '不知道', 'uncertain', 'unclear', '是指', '是不是', '可能', 'might be', 'could be', '需要澄清']
        has_uncertainty = any(keyword in response_lower for keyword in uncertainty_keywords)
        
        if has_uncertainty and 'select' in response_lower:
            # Extract the SQL part
            sql_start = response.find('SELECT')
            if sql_start == -1:
                sql_start = response.find('select')
            
            if sql_start >= 0:
                # Look for DISTINCT type queries (common intermediate pattern)
                if 'distinct' in response_lower[sql_start:sql_start+200]:
                    sql_end = response.find('\n\n', sql_start)
                    if sql_end > 0:
                        intermediate_sql = response[sql_start:sql_end].strip()
                    else:
                        # Try to find end of SQL statement
                        sql_end = response.find(';', sql_start)
                        if sql_end > 0:
                            intermediate_sql = response[sql_start:sql_end+1].strip()
                        else:
                            intermediate_sql = response[sql_start:].strip()
                    
                    intermediate_sql = VannaManager._clean_sql(intermediate_sql)
                    if 'SELECT' in intermediate_sql.upper() and 'DISTINCT' in intermediate_sql.upper():
                        return intermediate_sql
        
        return ""

    @staticmethod
    def _is_clarification_request(response: str) -> bool:
        """
        Check if LLM response is asking for clarification rather than providing SQL.
        
        Returns:
            bool: True if response appears to be a clarification request
        """
        if not response or not isinstance(response, str):
            return False
        
        response_lower = response.lower()
        
        # Keywords indicating clarification needed
        clarification_patterns = [
            '无法确定', '不确定', '需要更多信息', '请明确', '请指定',
            'cannot determine', 'unclear', 'need more information', 
            'please clarify', 'please specify', 'could you clarify',
            '请问', '是指', '是不是', '的意思',
            'do you mean', 'what do you mean', 'which',
            '没有找到', 'not found', 'cannot find'
        ]
        
        has_clarification = any(pattern in response_lower for pattern in clarification_patterns)
        
        # Also check if response doesn't contain valid SQL
        has_sql = 'select' in response_lower and 'from' in response_lower
        
        # If it has clarification keywords and no SQL, it's likely a clarification request
        # OR if it has clarification keywords and very short SQL (< 50 chars), might be incomplete
        if has_clarification:
            if not has_sql:
                return True
            else:
                # Extract potential SQL and check if it's complete
                sql_part = response[response_lower.find('select'):]
                if len(sql_part.strip()) < 50:  # Too short to be a real query
                    return True
        
        return False

    @staticmethod
    def _clean_sql(sql: str) -> str:
        """
        Clean and normalize SQL string from AI output.
        Removes markdown code blocks and extra whitespace.
        """
        if not sql or not isinstance(sql, str):
            raise ValueError("Invalid SQL output")
        
        sql = sql.strip()
        
        # Remove markdown code blocks
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1] if "\n" in sql else sql
            if sql.endswith("```"):
                sql = sql.rsplit("\n", 1)[0]
        
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        return sql
    
    @staticmethod
    def generate_summary(question: str, df: pd.DataFrame, dataset_id: int) -> str:
        """
        Generate AI-powered business summary of query results.
        
        Args:
            question: User's original question
            df: Query result DataFrame
            dataset_id: Dataset ID for Vanna instance
            
        Returns:
            str: AI-generated summary text (100 words max, in Chinese)
        """
        if df is None or df.empty:
            return "数据为空，无法生成总结。"
        
        try:
            # Get Vanna instance for LLM
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # 1. Prepare data preview
            # Convert head (max 5 rows) to markdown table
            data_preview_parts = []
            
            # Add head data
            head_df = df.head(5)
            data_preview_parts.append("前 5 行数据：")
            data_preview_parts.append(head_df.to_markdown(index=False))
            
            # Add statistical description if contains numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                describe_df = df[numeric_cols].describe()
                data_preview_parts.append("\n统计描述：")
                data_preview_parts.append(describe_df.to_markdown())
            
            data_preview = "\n".join(data_preview_parts)
            
            # 2. Construct prompt
            prompt = f"""用户问题：{question}

查询结果数据如下：
{data_preview}

请基于上述数据，用一段简练的中文总结数据趋势或关键发现（100字以内）。

要求：
1. 直接输出总结文字，不要添加“总结：”等前缀
2. 用业务语言，避免技术词汇
3. 突出关键数字和趋势
4. 保持简洁、友好"""
            
            # 3. Call LLM
            summary = vn.submit_prompt(prompt)
            
            # 4. Clean and validate
            summary = summary.strip()
            
            # Remove common prefixes
            prefixes_to_remove = ["总结：", "分析：", "AI总结：", "数据分析："]
            for prefix in prefixes_to_remove:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            
            # Limit length (just in case LLM ignores the limit)
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "总结生成失败，请稍后再试。"
    
    @staticmethod
    def generate_data_insight(question: str, sql: str, df: pd.DataFrame, dataset_id: int) -> str:
        """
        Generate AI-powered business insight as an analyst agent.
        Compresses data into a summary before sending to LLM to reduce token usage.
        
        Args:
            question: User's original question
            sql: SQL query that generated the data
            df: Query result DataFrame
            dataset_id: Dataset ID for Vanna instance
            
        Returns:
            str: AI-generated business insight (Markdown format, in Chinese)
        """
        if df is None or df.empty:
            return "数据为空，无法生成业务分析。"
        
        try:
            # Get Vanna instance for LLM
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # === 数据压缩策略 ===
            data_summary_parts = []
            
            # 1. 前 5 行数据（使用 markdown 表格格式）
            head_df = df.head(5)
            data_summary_parts.append("### 数据样本（前 5 行）")
            data_summary_parts.append(head_df.to_markdown(index=False))
            
            # 2. 数值列的统计描述
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                describe_df = df[numeric_cols].describe()
                data_summary_parts.append("\n### 统计描述（数值列）")
                data_summary_parts.append(describe_df.to_markdown())
            
            # 3. 数据元信息
            data_summary_parts.append(f"\n### 数据元信息")
            data_summary_parts.append(f"- 列名：{', '.join(df.columns.tolist())}")
            data_summary_parts.append(f"- 数据总量：{len(df)} 行")
            
            data_summary = "\n".join(data_summary_parts)
            
            # === Prompt 设计：扮演高级商业分析师 ===
            system_prompt = """你是一位资深的商业数据分析师，擅长从数据中挖掘洞察和趋势。
你的任务是基于用户的问题、SQL 查询逻辑和数据摘要，提供简洁的业务分析。

分析要求：
1. 使用 Markdown 格式输出
2. 重点关注数据趋势、异常值、关键发现
3. 用业务语言，避免技术术语
4. 篇幅控制在 150 字以内
5. 直接输出分析内容，不要添加"分析："等前缀
6. 使用中文"""
            
            user_prompt = f"""用户问题：
{question}

SQL 查询逻辑：
```sql
{sql}
```

{data_summary}

请基于以上信息，提供业务洞察分析："""
            
            # === 调用 LLM ===
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            insight = vn.submit_prompt(messages)
            
            # === 清理和验证 ===
            insight = insight.strip()
            
            # 移除常见前缀
            prefixes_to_remove = ["分析：", "业务洞察：", "AI 分析：", "数据洞察：", "总结："]
            for prefix in prefixes_to_remove:
                if insight.startswith(prefix):
                    insight = insight[len(prefix):].strip()
            
            # 长度限制（防止 LLM 忽略指令）
            if len(insight) > 300:
                insight = insight[:300] + "..."
            
            logger.info(f"Generated insight for dataset {dataset_id}: {insight[:50]}...")
            return insight
            
        except Exception as e:
            logger.error(f"Failed to generate data insight: {e}")
            return "业务分析生成失败，请稍后再试。"
    
    @staticmethod
    def analyze_relationships(dataset_id: int, table_names: list[str], db_session: Session) -> dict:
        """
        Use LLM to analyze potential relationships between tables.
        
        Args:
            dataset_id: Dataset ID
            table_names: List of table names to analyze
            db_session: Database session
            
        Returns:
            dict: {
                'edges': [{'source': 'users', 'target': 'orders', 'source_col': 'id', 'target_col': 'user_id', 'type': 'left'}],
                'nodes': [{'table_name': 'users', 'fields': [...]}]
            }
        """
        try:
            # Get dataset and datasource
            stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
            result = db_session.execute(stmt)
            dataset = result.scalars().first()
            
            if not dataset or not dataset.datasource:
                raise ValueError("数据集或数据源不存在")
            
            datasource = dataset.datasource
            
            # 1. Get DDLs for all tables
            ddl_list = []
            nodes = []
            
            # Get engine and inspector once
            engine = DBInspector.get_engine(datasource)
            inspector = inspect(engine)
            
            for table_name in table_names:
                try:
                    # Get table columns using inspector (faster than DDL generation)
                    columns = inspector.get_columns(table_name)
                    
                    # Build simple DDL representation
                    ddl_parts = [f"CREATE TABLE {table_name} ("]
                    col_definitions = []
                    for col in columns:
                        col_def = f"  {col['name']} {str(col['type'])}"
                        if not col.get('nullable', True):
                            col_def += " NOT NULL"
                        col_definitions.append(col_def)
                    ddl_parts.append(",\n".join(col_definitions))
                    ddl_parts.append(")")
                    ddl = "\n".join(ddl_parts)
                    
                    ddl_list.append(f"-- {table_name}\n{ddl}")
                    
                    # Build fields for nodes
                    fields = []
                    for col in columns:
                        fields.append({
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col.get('nullable', True)
                        })
                    
                    nodes.append({
                        'table_name': table_name,
                        'fields': fields
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to get structure for {table_name}: {e}")
                    # Try to continue with other tables
                    continue
            
            if not ddl_list:
                raise ValueError("无法获取表结构信息")
            
            # 2. Construct prompt for LLM
            ddl_content = "\n\n".join(ddl_list)
            
            # Optimized prompt for strict JSON output
            prompt = f"""Analyze the following database table structures and identify potential foreign key relationships:

{ddl_content}

Analysis rules:
1. Look for naming patterns (e.g., user_id likely references users.id)
2. Consider common relationship patterns (order_id, product_id, customer_id, etc.)
3. Verify field type compatibility
4. Consider business logic reasonability

**CRITICAL**: Strictly return ONLY a JSON array. Do not use Markdown formatting. No explanation. No code blocks.

Expected format:
[{{
  "source": "table_a",
  "target": "table_b",
  "source_col": "id",
  "target_col": "a_id",
  "type": "left",
  "confidence": "high"
}}]

If no relationships found, return: []

Your response (JSON array only):"""
            
            # 3. Call LLM directly using OpenAI client to avoid ChromaDB conflicts
            # Using direct API call instead of Vanna instance
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": "You are a database relationship analyzer. You analyze table structures and return JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Lower temperature for more structured output
            )
            
            llm_response = response.choices[0].message.content
            
            logger.info(f"LLM relationship analysis response: {llm_response}")
            
            # 4. Enhanced JSON parsing with robust cleaning
            try:
                # Step 1: Clean markdown code blocks
                cleaned_response = llm_response.strip()
                
                # Remove markdown code block markers (```json, ```, etc.)
                cleaned_response = re.sub(r'^```(?:json)?\s*', '', cleaned_response, flags=re.IGNORECASE)
                cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
                cleaned_response = cleaned_response.strip()
                
                # Step 2: Try direct JSON parsing
                try:
                    edges = json.loads(cleaned_response)
                    logger.info("JSON parsed successfully on first attempt")
                except json.JSONDecodeError as e:
                    logger.warning(f"First JSON parse failed: {e}. Attempting regex extraction...")
                    
                    # Step 3: Try extracting JSON array using regex
                    match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                    if match:
                        json_str = match.group()
                        edges = json.loads(json_str)
                        logger.info("JSON extracted and parsed successfully using regex")
                    else:
                        # Step 4: Last resort - try to find any valid JSON structure
                        # Look for content between first [ and last ]
                        start_idx = cleaned_response.find('[')
                        end_idx = cleaned_response.rfind(']')
                        
                        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                            json_str = cleaned_response[start_idx:end_idx + 1]
                            edges = json.loads(json_str)
                            logger.info("JSON parsed successfully using index-based extraction")
                        else:
                            # No valid JSON found, return empty
                            logger.error(f"Could not find valid JSON array in response: {cleaned_response[:200]}")
                            edges = []
                
                # Validate structure
                if not isinstance(edges, list):
                    logger.warning(f"LLM response is not a list, wrapping in list: {type(edges)}")
                    edges = [edges] if isinstance(edges, dict) else []
                
                # Filter and validate edges
                valid_edges = []
                for edge in edges:
                    if isinstance(edge, dict) and all(k in edge for k in ['source', 'target', 'source_col', 'target_col']):
                        # Ensure type is set
                        if 'type' not in edge:
                            edge['type'] = 'left'
                        # Ensure confidence is set
                        if 'confidence' not in edge:
                            edge['confidence'] = 'medium'
                        valid_edges.append(edge)
                    else:
                        logger.warning(f"Skipping invalid edge structure: {edge}")
                
                logger.info(f"Analyzed {len(valid_edges)} valid relationships between {len(table_names)} tables")
                
                return {
                    'edges': valid_edges,
                    'nodes': nodes
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response after all attempts: {e}")
                logger.error(f"Raw response: {llm_response}")
                logger.error(f"Cleaned response: {cleaned_response[:500]}")
                # Return empty edges if parsing fails
                return {
                    'edges': [],
                    'nodes': nodes
                }
            except Exception as e:
                logger.error(f"Unexpected error during JSON parsing: {e}")
                return {
                    'edges': [],
                    'nodes': nodes
                }
        
        except Exception as e:
            logger.error(f"Failed to analyze relationships: {e}")
            raise ValueError(f"关联分析失败: {str(e)}")
