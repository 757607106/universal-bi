"""
Vanna 分析服务

提供业务分析、数据洞察和表关系分析功能。
"""

import re
import json
import pandas as pd
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, inspect
from openai import OpenAI as OpenAIClient

from app.models.metadata import Dataset
from app.core.config import settings
from app.core.logger import get_logger
from app.services.db_inspector import DBInspector
from app.services.vanna.instance_manager import VannaInstanceManager

logger = get_logger(__name__)


class VannaAnalystService:
    """
    Vanna 分析服务

    提供业务分析、数据洞察和表关系分析功能。
    """

    @classmethod
    def generate_summary(cls, question: str, df: pd.DataFrame, dataset_id: int) -> str:
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
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)

            # Prepare data preview
            data_preview_parts = []

            head_df = df.head(5)
            data_preview_parts.append("前 5 行数据：")
            data_preview_parts.append(head_df.to_markdown(index=False))

            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                describe_df = df[numeric_cols].describe()
                data_preview_parts.append("\n统计描述：")
                data_preview_parts.append(describe_df.to_markdown())

            data_preview = "\n".join(data_preview_parts)

            prompt = f"""用户问题：{question}

查询结果数据如下：
{data_preview}

请基于上述数据，用一段简练的中文总结数据趋势或关键发现（100字以内）。

要求：
1. 直接输出总结文字，不要添加"总结："等前缀
2. 用业务语言，避免技术词汇
3. 突出关键数字和趋势
4. 保持简洁、友好"""

            summary = vn.submit_prompt(prompt)
            summary = summary.strip()

            # Remove common prefixes
            prefixes_to_remove = ["总结：", "分析：", "AI总结：", "数据分析："]
            for prefix in prefixes_to_remove:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()

            if len(summary) > 200:
                summary = summary[:200] + "..."

            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "总结生成失败，请稍后再试。"

    @classmethod
    def generate_data_insight(cls, question: str, sql: str, df: pd.DataFrame, dataset_id: int) -> str:
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
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)

            # === 数据压缩策略 ===
            data_summary_parts = []

            head_df = df.head(5)
            data_summary_parts.append("### 数据样本（前 5 行）")
            data_summary_parts.append(head_df.to_markdown(index=False))

            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                describe_df = df[numeric_cols].describe()
                data_summary_parts.append("\n### 统计描述（数值列）")
                data_summary_parts.append(describe_df.to_markdown())

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

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            insight = vn.submit_prompt(messages)
            insight = insight.strip()

            # 移除常见前缀
            prefixes_to_remove = ["分析：", "业务洞察：", "AI 分析：", "数据洞察：", "总结："]
            for prefix in prefixes_to_remove:
                if insight.startswith(prefix):
                    insight = insight[len(prefix):].strip()

            if len(insight) > 300:
                insight = insight[:300] + "..."

            logger.info(f"Generated insight for dataset {dataset_id}: {insight[:50]}...")
            return insight

        except Exception as e:
            logger.error(f"Failed to generate data insight: {e}")
            return "业务分析生成失败，请稍后再试。"

    @classmethod
    def analyze_relationships(cls, dataset_id: int, table_names: list[str], db_session: Session) -> dict:
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
            stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
            result = db_session.execute(stmt)
            dataset = result.scalars().first()

            if not dataset or not dataset.datasource:
                raise ValueError("数据集或数据源不存在")

            datasource = dataset.datasource

            # Get DDLs for all tables
            ddl_list = []
            nodes = []

            engine = DBInspector.get_engine(datasource)
            inspector = inspect(engine)

            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)

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
                    continue

            if not ddl_list:
                raise ValueError("无法获取表结构信息")

            ddl_content = "\n\n".join(ddl_list)

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

            # Call LLM directly using OpenAI client
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
                temperature=0.1
            )

            llm_response = response.choices[0].message.content
            logger.info(f"LLM relationship analysis response: {llm_response}")

            # Enhanced JSON parsing
            try:
                cleaned_response = llm_response.strip()

                # Remove markdown code block markers
                cleaned_response = re.sub(r'^```(?:json)?\s*', '', cleaned_response, flags=re.IGNORECASE)
                cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
                cleaned_response = cleaned_response.strip()

                try:
                    edges = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                    if match:
                        edges = json.loads(match.group())
                    else:
                        start_idx = cleaned_response.find('[')
                        end_idx = cleaned_response.rfind(']')

                        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                            edges = json.loads(cleaned_response[start_idx:end_idx + 1])
                        else:
                            edges = []

                if not isinstance(edges, list):
                    edges = [edges] if isinstance(edges, dict) else []

                # Validate edges
                valid_edges = []
                for edge in edges:
                    if isinstance(edge, dict) and all(k in edge for k in ['source', 'target', 'source_col', 'target_col']):
                        if 'type' not in edge:
                            edge['type'] = 'left'
                        if 'confidence' not in edge:
                            edge['confidence'] = 'medium'
                        valid_edges.append(edge)

                logger.info(f"Analyzed {len(valid_edges)} valid relationships between {len(table_names)} tables")

                return {
                    'edges': valid_edges,
                    'nodes': nodes
                }

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                return {
                    'edges': [],
                    'nodes': nodes
                }

        except Exception as e:
            logger.error(f"Failed to analyze relationships: {e}")
            raise ValueError(f"关联分析失败: {str(e)}")
