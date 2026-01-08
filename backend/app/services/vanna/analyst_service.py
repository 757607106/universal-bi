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

    @classmethod
    def generate_suggested_questions(cls, dataset_id: int, db_session: Session, limit: int = 5) -> list[str]:
        """
        Generate suggested questions based on dataset schema metadata.

        Args:
            dataset_id: Dataset ID
            db_session: Database session
            limit: Number of questions to generate (default: 5)

        Returns:
            list[str]: List of suggested questions
        """
        try:
            # Get dataset and datasource info
            stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
            result = db_session.execute(stmt)
            dataset = result.scalars().first()

            if not dataset or not dataset.datasource:
                logger.warning(f"Dataset {dataset_id} or datasource not found")
                return cls._get_default_questions()

            # Get schema metadata (table names and key fields)
            schema_tables = dataset.schema_config or []
            if not schema_tables:
                logger.warning(f"Dataset {dataset_id} has no schema_config")
                return cls._get_default_questions()

            datasource = dataset.datasource
            engine = DBInspector.get_engine(datasource)
            inspector = inspect(engine)

            # Gather metadata
            tables_metadata = []
            for table_name in schema_tables[:10]:  # Limit to 10 tables to avoid prompt overflow
                try:
                    columns = inspector.get_columns(table_name)
                    # Extract key fields (id, name, amount, date, etc.)
                    key_fields = []
                    for col in columns:
                        col_name_lower = col['name'].lower()
                        # Prioritize meaningful business fields
                        if any(keyword in col_name_lower for keyword in ['id', 'name', 'amount', 'price', 'total', 'date', 'time', 'status', 'count', 'quantity']):
                            key_fields.append(col['name'])
                    
                    tables_metadata.append({
                        'table': table_name,
                        'key_fields': key_fields[:5]  # Limit to 5 key fields per table
                    })
                except Exception as e:
                    logger.warning(f"Failed to get columns for {table_name}: {e}")
                    continue

            if not tables_metadata:
                logger.warning(f"No table metadata retrieved for dataset {dataset_id}")
                return cls._get_default_questions()

            # Build prompt
            metadata_desc = "\n".join([
                f"- {item['table']}: {', '.join(item['key_fields'])}" 
                for item in tables_metadata
            ])

            prompt = f"""作为一个商业智能分析师,请根据以下数据库结构,生成 {limit} 个用户最可能感兴趣的业务分析问题。

数据库表结构:
{metadata_desc}

要求:
1. 问题要具体、业务导向,不要包含 SQL 代码
2. 每个问题一行,直接输出问题文本
3. 使用中文
4. 问题应涵盖统计、趋势、排名、分布等不同分析维度
5. 不要添加编号或前缀,直接输出问题列表

请生成 {limit} 个问题:"""

            # Call LLM
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个商业智能分析师,擅长生成业务分析问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            llm_response = response.choices[0].message.content.strip()
            logger.info(f"LLM suggested questions response: {llm_response[:200]}...")

            # Parse response into list of questions
            questions = cls._parse_questions_from_llm(llm_response, limit)
            
            if not questions:
                logger.warning(f"Failed to parse questions from LLM response")
                return cls._get_default_questions()

            return questions[:limit]

        except Exception as e:
            logger.error(f"Failed to generate suggested questions: {e}")
            return cls._get_default_questions()

    @staticmethod
    def _parse_questions_from_llm(llm_response: str, limit: int) -> list[str]:
        """
        Parse LLM response into a list of questions.
        
        Handles various formats:
        - Numbered list (1. question)
        - Bullet points (- question)
        - Plain lines
        """
        questions = []
        lines = llm_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove common prefixes
            line = re.sub(r'^[\d]+\.\s*', '', line)  # Remove "1. "
            line = re.sub(r'^[-*•]\s*', '', line)     # Remove "- ", "* ", "• "
            line = re.sub(r'^\(\d+\)\s*', '', line)   # Remove "(1) "
            
            if len(line) > 10:  # Valid question should be at least 10 chars
                questions.append(line)
        
        return questions[:limit]

    @staticmethod
    def _get_default_questions() -> list[str]:
        """
        Return a default set of generic business analysis questions.
        """
        return [
            "最近一个月的销售额趋势如何?",
            "哪些产品的销售量最高?",
            "不同地区的业务分布情况如何?",
            "最活跃的用户有哪些特征?",
            "本月与上月相比,关键指标有何变化?"
        ]
