from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models.metadata import Dataset
from app.core.config import settings
from app.services.db_inspector import DBInspector
from datetime import datetime, date
from decimal import Decimal
import logging
import re
import asyncio
import pandas as pd
import uuid
from openai import OpenAI as OpenAIClient

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


class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Legacy Vanna class for SQL generation
    Combines ChromaDB vector store with OpenAI chat
    """
    def __init__(self, config=None):
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
    @staticmethod
    def get_legacy_vanna(dataset_id: int):
        """
        Initialize and return a Legacy Vanna instance for SQL generation.
        Uses the same configuration as Agent but with Legacy API.
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        vn = VannaLegacy(config={
            'api_key': settings.DASHSCOPE_API_KEY,
            'model': settings.QWEN_MODEL,
            'path': './chroma_db',
            'n_results': 10,
            'client': 'persistent',
            'collection_name': collection_name,
            'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        })
        
        # Enable data visibility for LLM to support intermediate_sql reasoning
        vn.allow_llm_to_see_data = True
        
        return vn

    @staticmethod
    def get_agent(dataset_id: int):
        """
        Initialize and return a configured Vanna Agent instance (Vanna 2.0).
        """
        collection_name = f"vec_ds_{dataset_id}"
        
        # 1. LLM Service (Qwen via OpenAI compatible API)
        llm_service = OpenAILlmService(
            api_key=settings.DASHSCOPE_API_KEY,
            model=settings.QWEN_MODEL,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 2. Agent Memory (ChromaDB)
        # We use a local persist directory for simplicity.
        # In production, this should be configurable.
        agent_memory = ChromaAgentMemory(
            persist_directory="./chroma_db",
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
        
        return agent

    @staticmethod
    def train_dataset(dataset_id: int, table_names: list[str], db_session: Session):
        """
        Train the dataset by extracting DDLs and feeding them to Vanna Memory.
        This wrapper handles the sync-to-async bridge.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(VannaManager.train_dataset_async(dataset_id, table_names, db_session))

    @staticmethod
    async def train_dataset_async(dataset_id: int, table_names: list[str], db_session: Session):
        """
        Async implementation of training logic.
        """
        logger.info(f"Starting training for dataset {dataset_id}")
        
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.error(f"Dataset {dataset_id} not found")
            return
            
        dataset.training_status = "training"
        db_session.commit()
        
        try:
            datasource = dataset.datasource
            if not datasource:
                raise ValueError("DataSource associated with dataset not found")
            
            # 1. Initialize Agent
            agent = VannaManager.get_agent(dataset_id)
            
            # 2. Extract DDLs
            ddls = []
            for table_name in table_names:
                try:
                    ddl = DBInspector.get_table_ddl(datasource, table_name)
                    ddls.append(ddl)
                except Exception as e:
                    logger.warning(f"Failed to get DDL for {table_name}: {e}")
            
            # 3. Feed to Vanna (Memory)
            user = User(id="admin", email="admin@example.com", group_memberships=['admin'])
            context = ToolContext(
                user=user,
                conversation_id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4()),
                agent_memory=agent.agent_memory
            )
            
            for ddl in ddls:
                if ddl:
                    await agent.agent_memory.save_text_memory(content=ddl, context=context)
            
            # 4. Update Status
            dataset.training_status = "completed"
            dataset.last_trained_at = datetime.utcnow()
            db_session.commit()
            logger.info(f"Training completed for dataset {dataset_id}")
            
        except Exception as e:
            logger.error(f"Training failed for dataset {dataset_id}: {e}")
            dataset.training_status = "failed"
            db_session.commit()

    @staticmethod
    def train_term(dataset_id: int, term: str, definition: str, db_session: Session):
        """
        Train a business term by adding it to Vanna's documentation memory.
        Uses Legacy API for consistency with existing training approach.
        """
        try:
            # Get Legacy Vanna instance
            vn = VannaManager.get_legacy_vanna(dataset_id)
            
            # Format as documentation and train
            doc_content = f"业务术语: {term}\n定义: {definition}"
            vn.train(documentation=doc_content)
            
            logger.info(f"Successfully trained business term '{term}' for dataset {dataset_id}")
            
        except Exception as e:
            logger.error(f"Failed to train business term '{term}': {e}")
            raise ValueError(f"训练业务术语失败: {str(e)}")

    @staticmethod
    async def generate_result(dataset_id: int, question: str, db_session: Session):
        """
        Generate SQL and execute it with intelligent multi-round dialogue (Auto-Reflection Loop).
        
        Features:
        1. LLM-driven intermediate SQL detection and execution
        2. Intelligent clarification generation when ambiguous
        3. Graceful text-only responses (no exceptions for non-SQL)
        4. LLM-powered friendly error messages on failures
        5. All responses in Chinese
        """
        execution_steps = []
        
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
                
                try:
                    # Execute the SQL
                    df = pd.read_sql(cleaned_sql, engine)
                    execution_steps.append(f"SQL 执行成功，返回 {len(df)} 行")
                    logger.info(f"SQL executed successfully: {len(df)} rows")
                    
                    # Chart Type Inference
                    chart_type = VannaManager._infer_chart_type(df)
                    execution_steps.append(f"推断图表类型: {chart_type}")
                    
                    # Serialize data
                    cleaned_rows = VannaManager._serialize_dataframe(df)
                    
                    return {
                        "sql": cleaned_sql,
                        "columns": df.columns.tolist(),
                        "rows": cleaned_rows,
                        "chart_type": chart_type,
                        "summary": None,
                        "steps": execution_steps
                    }
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"SQL execution failed: {error_msg}")
                    execution_steps.append(f"SQL 执行失败: {error_msg[:100]}")
                    
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
