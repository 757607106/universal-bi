"""
Vanna 2.0 Agent 管理器

提供 Vanna 2.0 Agent API 的封装，支持流式对话和工具调用。
"""

import uuid

from vanna.core import Agent, ToolRegistry
from vanna.core.user import RequestContext
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory

from app.core.config import settings
from app.core.logger import get_logger
from app.services.vanna.base import SimpleUserResolver
from app.services.vanna.instance_manager import VannaInstanceManager

logger = get_logger(__name__)


class VannaAgentManager:
    """
    Vanna 2.0 Agent 管理器

    使用 Agent API 进行对话式 SQL 生成，提供：
    - 流式响应支持
    - 工具执行机制 (SQL 生成、SQL 执行)
    - 上下文增强 (DDL、文档、问答示例)
    - 对话历史管理

    与 VannaManager (Legacy) 并行运行，通过 /agent-chat 端点提供服务。
    """

    _agent_instances: dict = {}  # {dataset_id: Agent}

    @classmethod
    def get_agent(cls, dataset_id: int, datasource) -> Agent:
        """
        获取或创建 Vanna Agent 实例

        Args:
            dataset_id: 数据集 ID
            datasource: 数据源对象

        Returns:
            配置好的 Agent 实例
        """
        if dataset_id in cls._agent_instances:
            logger.debug(f"Reusing existing Agent instance for dataset {dataset_id}")
            return cls._agent_instances[dataset_id]

        agent = cls._create_agent(dataset_id, datasource)
        cls._agent_instances[dataset_id] = agent
        logger.info(f"Created new VannaAgentManager Agent for dataset {dataset_id}")
        return agent

    @classmethod
    def _create_agent(cls, dataset_id: int, datasource) -> Agent:
        """
        创建新的 Agent 实例

        Args:
            dataset_id: 数据集 ID
            datasource: 数据源对象

        Returns:
            配置好的 Agent 实例
        """
        from app.services.vanna_tools import GenerateSqlTool, ExecuteSqlTool, GetSchemaInfoTool
        from app.services.vanna_enhancer import MultilingualContextEnhancer

        # 1. 创建 LLM 服务
        llm_service = OpenAILlmService(
            model=settings.QWEN_MODEL,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # 2. 创建 Agent Memory (ChromaDB)
        collection_name = f"agent_ds_{dataset_id}"
        agent_memory = ChromaAgentMemory(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=collection_name
        )

        # 3. 获取 Legacy Vanna 实例 (复用现有训练数据)
        vanna_legacy = VannaInstanceManager.get_legacy_vanna(dataset_id)

        # 4. 注册工具
        registry = ToolRegistry()
        registry.register(GenerateSqlTool(vanna_legacy, datasource))
        registry.register(ExecuteSqlTool(datasource))
        registry.register(GetSchemaInfoTool(vanna_legacy, datasource))

        # 5. 创建 Context Enhancer (多语言版本，默认中文)
        enhancer = MultilingualContextEnhancer(
            agent_memory=agent_memory,
            vanna_legacy=vanna_legacy,
            language="中文",
            max_ddl=5,
            max_docs=3,
            max_qa=5
        )

        # 6. 创建 Agent
        agent = Agent(
            llm_service=llm_service,
            tool_registry=registry,
            user_resolver=SimpleUserResolver(),
            agent_memory=agent_memory,
            llm_context_enhancer=enhancer
        )

        return agent

    @classmethod
    async def chat(
        cls,
        dataset_id: int,
        question: str,
        user_id: str,
        datasource,
        conversation_id: str = None
    ):
        """
        使用 Agent 进行对话 (生成器版本)

        Args:
            dataset_id: 数据集 ID
            question: 用户问题
            user_id: 用户 ID
            datasource: 数据源对象
            conversation_id: 对话 ID (可选)

        Yields:
            UiComponent: Agent 返回的 UI 组件
        """
        agent = cls.get_agent(dataset_id, datasource)

        # 创建请求上下文
        request_context = RequestContext(
            user_id=user_id,
            metadata={
                "dataset_id": dataset_id,
                "conversation_id": conversation_id or str(uuid.uuid4())
            }
        )

        try:
            # 发送消息并流式获取响应
            async for component in agent.send_message(
                request_context,
                question,
                conversation_id=conversation_id
            ):
                yield component

        except Exception as e:
            logger.error(f"Agent chat failed for dataset {dataset_id}: {e}", exc_info=True)
            # 返回错误组件
            from vanna.components import SimpleTextComponent
            yield SimpleTextComponent(
                text="抱歉，处理您的请求时发生错误。请稍后重试或换一种问法。"
            )

    @classmethod
    async def chat_simple(
        cls,
        dataset_id: int,
        question: str,
        user_id: str,
        datasource,
        conversation_id: str = None
    ) -> dict:
        """
        使用 Agent 进行对话 (简化版本，返回完整结果)

        用于需要一次性获取完整响应的场景。

        Args:
            dataset_id: 数据集 ID
            question: 用户问题
            user_id: 用户 ID
            datasource: 数据源对象
            conversation_id: 对话 ID (可选)

        Returns:
            dict: 包含响应内容的字典
        """
        components = []

        async for component in cls.chat(
            dataset_id=dataset_id,
            question=question,
            user_id=user_id,
            datasource=datasource,
            conversation_id=conversation_id
        ):
            components.append(component)

        # 组装响应
        response = {
            "components": [],
            "sql": None,
            "data": None,
            "error": None
        }

        for comp in components:
            comp_dict = {
                "type": comp.__class__.__name__
            }

            # 尝试提取组件内容
            if hasattr(comp, 'text'):
                comp_dict["text"] = comp.text
            if hasattr(comp, 'content'):
                comp_dict["content"] = comp.content
            if hasattr(comp, 'markdown'):
                comp_dict["markdown"] = comp.markdown
            if hasattr(comp, 'metadata'):
                comp_dict["metadata"] = comp.metadata
                # 提取 SQL 和数据
                if isinstance(comp.metadata, dict):
                    if 'sql' in comp.metadata:
                        response["sql"] = comp.metadata["sql"]
                    if 'data' in comp.metadata:
                        response["data"] = comp.metadata["data"]

            response["components"].append(comp_dict)

        return response

    @classmethod
    def clear_agent_cache(cls, dataset_id: int = None):
        """
        清除 Agent 缓存

        Args:
            dataset_id: 数据集 ID。如果为 None，清除所有缓存。
        """
        if dataset_id is not None:
            if dataset_id in cls._agent_instances:
                del cls._agent_instances[dataset_id]
                logger.info(f"Cleared Agent cache for dataset {dataset_id}")
        else:
            cls._agent_instances.clear()
            logger.info("Cleared all Agent caches")
