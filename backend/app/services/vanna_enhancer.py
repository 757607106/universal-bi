"""
Vanna 2.0 LLM Context Enhancer

自定义 LLM 上下文增强器，用于在 Agent 调用 LLM 前注入相关的 DDL、文档和问答示例。
"""

import logging
from typing import TYPE_CHECKING, List, Optional

from vanna.core.enhancer import LlmContextEnhancer

if TYPE_CHECKING:
    from vanna.core.user.models import User
    from vanna.core.llm.models import LlmMessage
    from vanna.capabilities.agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class VannaContextEnhancer(LlmContextEnhancer):
    """
    Vanna 上下文增强器

    增强 LLM 的 system prompt，注入：
    - 相关的数据库表结构 (DDL)
    - 业务文档
    - 类似问答示例

    这使得 LLM 能够基于已有知识生成更准确的 SQL。
    """

    def __init__(
        self,
        agent_memory: Optional["AgentMemory"],
        vanna_legacy,
        *,
        max_ddl: int = 5,
        max_docs: int = 3,
        max_qa: int = 5
    ):
        """
        初始化上下文增强器

        Args:
            agent_memory: Agent 记忆组件（用于搜索文本记忆）
            vanna_legacy: VannaLegacy 实例（用于访问训练数据）
            max_ddl: 最大 DDL 数量
            max_docs: 最大文档数量
            max_qa: 最大问答示例数量
        """
        self.agent_memory = agent_memory
        self.vn = vanna_legacy
        self.max_ddl = max_ddl
        self.max_docs = max_docs
        self.max_qa = max_qa

    async def enhance_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        user: "User"
    ) -> str:
        """
        增强 system prompt，注入相关上下文

        Args:
            system_prompt: 原始 system prompt
            user_message: 用户消息（用于相似度搜索）
            user: 当前用户

        Returns:
            增强后的 system prompt
        """
        try:
            enhanced_prompt = system_prompt

            # 1. 获取相关的 DDL
            ddl_section = await self._get_ddl_section(user_message)
            if ddl_section:
                enhanced_prompt += ddl_section

            # 2. 获取相关文档
            doc_section = await self._get_documentation_section(user_message)
            if doc_section:
                enhanced_prompt += doc_section

            # 3. 获取类似问答示例
            qa_section = await self._get_qa_section(user_message)
            if qa_section:
                enhanced_prompt += qa_section

            # 4. 从 Agent Memory 获取额外上下文（如果有）
            memory_section = await self._get_memory_section(user_message, user)
            if memory_section:
                enhanced_prompt += memory_section

            return enhanced_prompt

        except Exception as e:
            logger.warning(f"增强 system prompt 失败: {e}")
            # 失败时返回原始 prompt，不影响主流程
            return system_prompt

    async def _get_ddl_section(self, user_message: str) -> str:
        """获取 DDL 部分"""
        try:
            ddl_list = self.vn.get_related_ddl(user_message)

            if not ddl_list:
                return ""

            section = "\n\n## 相关数据库表结构\n\n"
            section += "以下是与问题相关的数据库表定义，请基于这些表结构生成 SQL：\n\n"

            for i, ddl in enumerate(ddl_list[:self.max_ddl], 1):
                section += f"### 表 {i}\n```sql\n{ddl}\n```\n\n"

            return section

        except Exception as e:
            logger.warning(f"获取 DDL 失败: {e}")
            return ""

    async def _get_documentation_section(self, user_message: str) -> str:
        """获取文档部分"""
        try:
            doc_list = self.vn.get_related_documentation(user_message)

            if not doc_list:
                return ""

            section = "\n\n## 业务文档\n\n"
            section += "以下是与问题相关的业务说明和术语定义：\n\n"

            for doc in doc_list[:self.max_docs]:
                section += f"- {doc}\n"

            return section

        except Exception as e:
            logger.warning(f"获取文档失败: {e}")
            return ""

    async def _get_qa_section(self, user_message: str) -> str:
        """获取问答示例部分"""
        try:
            qa_list = self.vn.get_similar_question_sql(user_message)

            if not qa_list:
                return ""

            section = "\n\n## 类似问答示例\n\n"
            section += "以下是类似问题的参考答案，可以借鉴其 SQL 写法：\n\n"

            for i, qa in enumerate(qa_list[:self.max_qa], 1):
                if isinstance(qa, dict) and 'question' in qa and 'sql' in qa:
                    section += f"### 示例 {i}\n"
                    section += f"**问题**: {qa['question']}\n"
                    section += f"**SQL**:\n```sql\n{qa['sql']}\n```\n\n"

            return section

        except Exception as e:
            logger.warning(f"获取问答示例失败: {e}")
            return ""

    async def _get_memory_section(self, user_message: str, user: "User") -> str:
        """从 Agent Memory 获取额外上下文"""
        if not self.agent_memory:
            return ""

        try:
            from vanna.core.tool import ToolContext
            import uuid

            # 创建临时上下文
            context = ToolContext(
                user=user,
                conversation_id="temp",
                request_id=str(uuid.uuid4()),
                agent_memory=self.agent_memory,
            )

            # 搜索相关的文本记忆
            memories = await self.agent_memory.search_text_memories(
                query=user_message,
                context=context,
                limit=3,
                similarity_threshold=0.7
            )

            if not memories:
                return ""

            section = "\n\n## 历史上下文\n\n"
            section += "来自历史对话的相关信息：\n\n"

            for result in memories:
                memory = result.memory
                section += f"- {memory.content}\n"

            return section

        except Exception as e:
            logger.warning(f"获取记忆上下文失败: {e}")
            return ""

    async def enhance_user_messages(
        self,
        messages: List["LlmMessage"],
        user: "User"
    ) -> List["LlmMessage"]:
        """
        增强用户消息

        默认实现不修改消息，子类可以覆盖此方法来：
        - 添加用户偏好信息
        - 注入用户特定的上下文
        - 修改消息格式

        Args:
            messages: 原始消息列表
            user: 当前用户

        Returns:
            增强后的消息列表
        """
        # 默认不修改
        return messages


class MultilingualContextEnhancer(VannaContextEnhancer):
    """
    多语言上下文增强器

    在 VannaContextEnhancer 基础上增加语言提示，
    确保 LLM 使用用户偏好的语言回复。
    """

    def __init__(
        self,
        agent_memory: Optional["AgentMemory"],
        vanna_legacy,
        *,
        language: str = "中文",
        max_ddl: int = 5,
        max_docs: int = 3,
        max_qa: int = 5
    ):
        """
        初始化多语言上下文增强器

        Args:
            agent_memory: Agent 记忆组件
            vanna_legacy: VannaLegacy 实例
            language: 响应语言（默认中文）
            max_ddl: 最大 DDL 数量
            max_docs: 最大文档数量
            max_qa: 最大问答示例数量
        """
        super().__init__(
            agent_memory,
            vanna_legacy,
            max_ddl=max_ddl,
            max_docs=max_docs,
            max_qa=max_qa
        )
        self.language = language

    async def enhance_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        user: "User"
    ) -> str:
        """增强 system prompt 并添加语言提示"""
        # 先调用父类方法增强上下文
        enhanced_prompt = await super().enhance_system_prompt(
            system_prompt, user_message, user
        )

        # 添加语言提示
        language_hint = f"\n\n## 响应要求\n\n请使用{self.language}回复用户的问题。"
        enhanced_prompt += language_hint

        return enhanced_prompt
