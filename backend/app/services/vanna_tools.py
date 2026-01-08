"""
Vanna 2.0 Agent Tools

自定义工具实现，用于 Vanna Agent 的 SQL 生成和执行功能。
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import text

from vanna.core.tool import Tool, ToolContext, ToolResult, ToolSchema
from vanna.components import UiComponent, SimpleTextComponent, RichTextComponent

from app.services.db_inspector import DBInspector

logger = logging.getLogger(__name__)


class GenerateSqlTool(Tool):
    """基于用户问题生成 SQL 查询的工具"""

    def __init__(self, vanna_legacy, datasource):
        """
        初始化 SQL 生成工具

        Args:
            vanna_legacy: VannaLegacy 实例，用于 SQL 生成
            datasource: 数据源对象
        """
        self.vn = vanna_legacy
        self.datasource = datasource

    async def get_schema(self, user) -> ToolSchema:
        """返回工具的 JSON Schema 定义"""
        return ToolSchema(
            name="generate_sql",
            description="根据自然语言问题生成 SQL 查询。当用户询问数据相关问题时使用此工具。",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户的自然语言问题，例如：'查询销售额最高的前10个产品'"
                    }
                },
                "required": ["question"]
            }
        )

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> ToolResult:
        """
        执行 SQL 生成

        Args:
            args: 包含 question 的参数字典
            context: 工具执行上下文

        Returns:
            ToolResult: 包含生成的 SQL 或错误信息
        """
        question = args.get("question", "")

        if not question.strip():
            return ToolResult(
                success=False,
                error="问题不能为空"
            )

        try:
            logger.info(f"正在为问题生成 SQL: {question[:100]}...")

            # 使用 Legacy API 生成 SQL，启用 allow_llm_to_see_data 以支持中间 SQL
            sql = self.vn.generate_sql(
                question + " (请用中文回答)",
                allow_llm_to_see_data=True
            )

            if not sql or sql.strip() == "":
                return ToolResult(
                    success=False,
                    error="无法为此问题生成有效的 SQL 查询"
                )

            # 检查是否是错误消息而非 SQL
            if sql.startswith("The LLM is not allowed") or "context is insufficient" in sql.lower():
                return ToolResult(
                    success=False,
                    error=sql
                )

            logger.info(f"SQL 生成成功: {sql[:200]}...")

            return ToolResult(
                success=True,
                result_for_llm=f"生成的 SQL 查询:\n```sql\n{sql}\n```\n\n请使用 execute_sql 工具执行此查询以获取结果。",
                ui_component=UiComponent(
                    rich_component=RichTextComponent(
                        content=f"**生成的 SQL 查询:**\n```sql\n{sql}\n```",
                        markdown=True
                    ),
                    simple_component=SimpleTextComponent(text=sql)
                )
            )

        except Exception as e:
            error_msg = f"SQL 生成失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )


class ExecuteSqlTool(Tool):
    """执行 SQL 查询并返回结果的工具"""

    def __init__(self, datasource):
        """
        初始化 SQL 执行工具

        Args:
            datasource: 数据源对象
        """
        self.datasource = datasource
        # SQL 结果行数限制
        self.max_rows = 100
        # 危险关键字列表
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
        ]

    async def get_schema(self, user) -> ToolSchema:
        """返回工具的 JSON Schema 定义"""
        return ToolSchema(
            name="execute_sql",
            description="执行 SQL 查询并返回结果数据。仅用于执行 SELECT 查询。",
            parameters={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "要执行的 SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        )

    def _is_safe_sql(self, sql: str) -> tuple[bool, Optional[str]]:
        """
        验证 SQL 是否安全（仅允许 SELECT 查询）

        Args:
            sql: SQL 查询语句

        Returns:
            tuple: (是否安全, 错误消息)
        """
        sql_upper = sql.upper().strip()

        # 检查是否以 SELECT 或 WITH 开头
        if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
            return False, "仅允许执行 SELECT 查询"

        # 检查危险关键字
        for keyword in self.dangerous_keywords:
            # 使用单词边界检查，避免误判
            import re
            if re.search(rf'\b{keyword}\b', sql_upper):
                return False, f"SQL 包含不允许的操作: {keyword}"

        return True, None

    def _add_limit_if_needed(self, sql: str) -> str:
        """
        如果 SQL 没有 LIMIT，添加默认限制

        Args:
            sql: 原始 SQL

        Returns:
            可能添加了 LIMIT 的 SQL
        """
        sql_upper = sql.upper().strip()

        # 如果已有 LIMIT，不修改
        if 'LIMIT' in sql_upper:
            return sql

        # 移除末尾分号（如果有）
        sql = sql.rstrip().rstrip(';')

        return f"{sql} LIMIT {self.max_rows}"

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> ToolResult:
        """
        执行 SQL 查询

        Args:
            args: 包含 sql 的参数字典
            context: 工具执行上下文

        Returns:
            ToolResult: 包含查询结果或错误信息
        """
        sql = args.get("sql", "")

        if not sql.strip():
            return ToolResult(
                success=False,
                error="SQL 查询不能为空"
            )

        # 验证 SQL 安全性
        is_safe, error_msg = self._is_safe_sql(sql)
        if not is_safe:
            return ToolResult(
                success=False,
                error=error_msg
            )

        # 添加 LIMIT 防止大结果集
        sql = self._add_limit_if_needed(sql)

        try:
            logger.info(f"正在执行 SQL: {sql[:200]}...")

            # 获取数据库引擎
            engine = DBInspector.get_engine(self.datasource)

            # 执行查询
            with engine.connect() as conn:
                df = pd.read_sql(text(sql), conn)

            row_count = len(df)
            col_count = len(df.columns)

            logger.info(f"SQL 执行成功，返回 {row_count} 行 {col_count} 列")

            # 格式化结果
            if row_count == 0:
                result_text = "查询执行成功，但没有返回任何数据。"
                result_for_llm = result_text
            else:
                # 将结果转为 JSON 格式（用于 LLM 分析）
                result_json = df.to_json(orient="records", force_ascii=False, date_format="iso")

                # 为 LLM 提供摘要
                result_for_llm = f"查询返回 {row_count} 行 {col_count} 列数据。\n\n"
                result_for_llm += f"列名: {', '.join(df.columns.tolist())}\n\n"

                # 如果数据量大，只显示前几行给 LLM
                if row_count > 20:
                    result_for_llm += f"前 20 行数据:\n{df.head(20).to_json(orient='records', force_ascii=False, date_format='iso')}"
                else:
                    result_for_llm += f"数据:\n{result_json}"

                result_text = f"查询返回 {row_count} 行数据"

            # 构建 UI 组件（显示 Markdown 表格）
            if row_count > 0:
                # 限制显示行数
                display_df = df.head(50)
                markdown_table = display_df.to_markdown(index=False)

                ui_content = f"**查询结果** ({row_count} 行):\n\n{markdown_table}"
                if row_count > 50:
                    ui_content += f"\n\n*仅显示前 50 行，共 {row_count} 行*"
            else:
                ui_content = "查询执行成功，但没有返回任何数据。"

            return ToolResult(
                success=True,
                result_for_llm=result_for_llm,
                ui_component=UiComponent(
                    rich_component=RichTextComponent(
                        content=ui_content,
                        markdown=True
                    ),
                    simple_component=SimpleTextComponent(text=result_text)
                ),
                metadata={
                    "row_count": row_count,
                    "col_count": col_count,
                    "columns": df.columns.tolist()
                }
            )

        except Exception as e:
            error_msg = f"SQL 执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )


class GetSchemaInfoTool(Tool):
    """获取数据库表结构信息的工具"""

    def __init__(self, vanna_legacy, datasource):
        """
        初始化表结构查询工具

        Args:
            vanna_legacy: VannaLegacy 实例
            datasource: 数据源对象
        """
        self.vn = vanna_legacy
        self.datasource = datasource

    async def get_schema(self, user) -> ToolSchema:
        """返回工具的 JSON Schema 定义"""
        return ToolSchema(
            name="get_schema_info",
            description="获取与问题相关的数据库表结构信息（DDL）。当需要了解表结构时使用。",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户问题或关键字，用于搜索相关的表结构"
                    }
                },
                "required": ["question"]
            }
        )

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> ToolResult:
        """
        获取相关的表结构信息

        Args:
            args: 包含 question 的参数字典
            context: 工具执行上下文

        Returns:
            ToolResult: 包含 DDL 信息
        """
        question = args.get("question", "")

        try:
            # 获取相关 DDL
            ddl_list = self.vn.get_related_ddl(question)

            if not ddl_list:
                return ToolResult(
                    success=True,
                    result_for_llm="没有找到与问题相关的表结构信息。",
                    ui_component=UiComponent(
                        simple_component=SimpleTextComponent(text="没有找到相关表结构")
                    )
                )

            # 格式化 DDL
            ddl_content = "\n\n".join([f"```sql\n{ddl}\n```" for ddl in ddl_list[:5]])

            return ToolResult(
                success=True,
                result_for_llm=f"找到 {len(ddl_list)} 个相关表结构:\n\n{ddl_content}",
                ui_component=UiComponent(
                    rich_component=RichTextComponent(
                        content=f"**相关表结构** ({len(ddl_list)} 个):\n\n{ddl_content}",
                        markdown=True
                    ),
                    simple_component=SimpleTextComponent(text=f"找到 {len(ddl_list)} 个相关表结构")
                )
            )

        except Exception as e:
            error_msg = f"获取表结构失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ToolResult(
                success=False,
                error=error_msg
            )
