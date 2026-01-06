from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models.metadata import Dataset
from app.core.config import settings
from app.services.db_inspector import DBInspector
from datetime import datetime, date
from decimal import Decimal
import logging
import uuid
import asyncio
import pandas as pd
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
        Generate SQL and execute it to get results with self-correction mechanism.
        Using Legacy API for better QA training compatibility.
        Implements automatic SQL error correction inspired by DB-GPT Agent.
        """
        max_retries = 2
        execution_steps = []
        
        # 1. Get Dataset with eager loading of datasource
        stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
        result = db_session.execute(stmt)
        dataset = result.scalars().first()
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Check if datasource is loaded
        if not dataset.datasource:
            raise ValueError("未找到关联的数据源配置")

        # 2. Get Legacy Vanna instance
        vn = VannaManager.get_legacy_vanna(dataset_id)

        # 3. Generate initial SQL using Legacy API
        try:
            # Legacy API's generate_sql method handles RAG automatically
            current_sql = vn.generate_sql(question)
            
            # Clean up SQL
            current_sql = VannaManager._clean_sql(current_sql)
            execution_steps.append("生成初始 SQL 查询")
            logger.info(f"Generated initial SQL: {current_sql}")

        except Exception as e:
            logger.error(f"SQL Generation failed: {e}")
            execution_steps.append(f"SQL 生成失败: {str(e)}")
            raise ValueError(f"Failed to generate SQL: {str(e)}")

        if not current_sql or "SELECT" not in current_sql.upper():
            execution_steps.append("AI 未能生成有效的 SELECT 查询")
            raise ValueError("AI failed to generate valid SQL query.")

        # 4. Execute Query with Self-Correction Loop
        engine = DBInspector.get_engine(dataset.datasource)
        df = None
        
        for attempt in range(max_retries + 1):
            try:
                # Attempt to execute SQL
                df = pd.read_sql(current_sql, engine)
                execution_steps.append(f"SQL 执行成功 (尝试 {attempt + 1}/{max_retries + 1})")
                logger.info(f"SQL executed successfully on attempt {attempt + 1}")
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"SQL Execution failed (Attempt {attempt + 1}/{max_retries + 1}): {error_msg}")
                execution_steps.append(f"SQL 执行失败 (尝试 {attempt + 1}): {error_msg[:100]}")
                
                if attempt == max_retries:
                    # Final attempt failed, give up
                    execution_steps.append("达到最大重试次数，SQL 自愈失败")
                    logger.error(f"SQL Execution failed after {max_retries + 1} attempts")
                    raise ValueError(f"SQL Execution Error: {error_msg}")
                
                # Self-Correction: Ask AI to fix the SQL
                try:
                    execution_steps.append("尝试 AI 自动修复 SQL")
                    
                    # Build correction prompt with error context
                    db_type = dataset.datasource.type.upper()
                    correction_prompt = f"""The following SQL query failed on {db_type} database:

SQL Query:
{current_sql}

Error Message:
{error_msg}

Please analyze the error and generate a corrected SQL query that:
1. Fixes the syntax or logical error
2. Works with {db_type} database
3. Still answers the original question: "{question}"

Generate ONLY the corrected SQL query, no explanations."""
                    
                    # Use submit_prompt for more control over correction
                    corrected_sql = vn.submit_prompt(correction_prompt)
                    corrected_sql = VannaManager._clean_sql(corrected_sql)
                    
                    if not corrected_sql or corrected_sql == current_sql:
                        logger.warning("AI failed to provide a different SQL correction")
                        execution_steps.append("AI 未能提供有效的修正方案")
                        continue  # Skip to next attempt with same SQL
                    
                    current_sql = corrected_sql
                    execution_steps.append(f"AI 已修正 SQL (尝试 {attempt + 2})")
                    logger.info(f"AI corrected SQL: {current_sql}")
                    
                except Exception as correction_error:
                    logger.error(f"SQL correction failed: {correction_error}")
                    execution_steps.append(f"SQL 修正过程出错: {str(correction_error)[:100]}")
                    # Continue with original SQL for next attempt

        # 5. Chart Type Inference
        chart_type = "table"
        if df is not None and not df.empty:
            # Check for date/time in column names for line chart
            lower_cols = [str(c).lower() for c in df.columns]
            has_date = any(x in c for c in lower_cols for x in ['date', 'time', 'year', 'month', 'day'])
            
            if len(df.columns) == 2 and has_date:
                # 2 columns + date usually implies time series
                chart_type = "line"
            elif len(df.columns) >= 2:
                # Check for 1 string/date and 1 number for bar chart
                dtypes = df.dtypes.values
                has_num = any(pd.api.types.is_numeric_dtype(t) for t in dtypes)
                has_str = any(pd.api.types.is_string_dtype(t) or pd.api.types.is_object_dtype(t) or pd.api.types.is_datetime64_any_dtype(t) for t in dtypes)
                if has_num and has_str:
                    # If we already decided it's line, stick to line, otherwise bar
                    if chart_type == "table":
                        chart_type = "bar"

        # 6. Formatting & Serialization
        def serialize(obj):
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            return obj

        rows = df.to_dict(orient='records')
        cleaned_rows = []
        for row in rows:
            new_row = {}
            for k, v in row.items():
                new_row[k] = serialize(v)
            cleaned_rows.append(new_row)

        return {
            "sql": current_sql,
            "columns": df.columns.tolist(),
            "rows": cleaned_rows,
            "chart_type": chart_type,
            "summary": None,
            "steps": execution_steps  # Include execution steps for debugging
        }

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
