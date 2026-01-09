"""
Vanna SQL 生成器

提供 SQL 生成、执行和智能反思循环功能。
"""

import re
import time
import pandas as pd
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.models.metadata import Dataset
from app.core.redis import redis_service, generate_cache_key
from app.core.logger import get_logger
from app.services.db_inspector import DBInspector
from app.services.duckdb_service import DuckDBService
from app.services.vanna.instance_manager import VannaInstanceManager
from app.services.vanna.cache_service import VannaCacheService
from app.services.vanna import utils
from app.services.chart_recommender import ChartRecommender
from app.services.query_rewriter import QueryRewriter
from typing import Optional, List, Dict

logger = get_logger(__name__)


class VannaSqlGenerator:
    """
    SQL 生成和执行服务

    提供智能 SQL 生成、多轮对话反思循环、缓存管理等功能。
    """

    @staticmethod
    def _execute_sql(dataset: Dataset, sql: str) -> pd.DataFrame:
        """
        执行 SQL 查询，自动识别数据源类型（DuckDB 或传统数据库）
        
        Args:
            dataset: Dataset 对象
            sql: SQL 查询语句
            
        Returns:
            pd.DataFrame: 查询结果
        """
        # 转义 SQL 中的 % 符号（仅对传统数据库）
        escaped_sql = sql.replace('%', '%%')
        
        # 判断是 DuckDB 还是传统数据库
        if dataset.duckdb_path:
            # 使用 DuckDB 执行（不需要转义%）
            logger.debug(f"Executing SQL on DuckDB: {dataset.duckdb_path}")
            df = DuckDBService.execute_query(dataset.duckdb_path, sql, read_only=True)
        else:
            # 使用传统数据库执行
            if not dataset.datasource:
                raise ValueError("Dataset has no datasource")
            
            logger.debug(f"Executing SQL on traditional datasource: {dataset.datasource.type}")
            engine = DBInspector.get_engine(dataset.datasource)
            df = pd.read_sql(escaped_sql, engine)
        
        return df

    @staticmethod
    def _detect_compound_query(question: str) -> bool:
        """
        检测是否是复合查询（需要返回多个结果）

        例如：
        - "全年销售额最高的月份和最低的月份分别是什么时候"
        - "订单金额最大和最小的客户分别是谁"
        - "销售额前3名和后3名的产品"

        Args:
            question: 用户问题

        Returns:
            bool: 是否是复合查询
        """
        compound_patterns = [
            # 最高/最大 和 最低/最小 组合
            r'(最高|最大|最多).{0,20}(和|与|以及|跟).{0,20}(最低|最小|最少)',
            r'(最低|最小|最少).{0,20}(和|与|以及|跟).{0,20}(最高|最大|最多)',
            # 第一/最好 和 最后/最差 组合
            r'(第一|最好|最优).{0,20}(和|与|以及).{0,20}(最后|最差|最劣)',
            r'(最后|最差|最劣).{0,20}(和|与|以及).{0,20}(第一|最好|最优)',
            # 前N名 和 后N名 组合
            r'(前\d+|TOP\s*\d+).{0,20}(和|与|以及).{0,20}(后\d+|BOTTOM\s*\d+)',
            r'(后\d+|BOTTOM\s*\d+).{0,20}(和|与|以及).{0,20}(前\d+|TOP\s*\d+)',
            # 分别/同时 + 多个极值
            r'分别.{0,30}(最|第一|前\d+|后\d+)',
            r'同时.{0,30}(最|第一|前\d+|后\d+)',
        ]

        for pattern in compound_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _get_compound_query_hint(question: str) -> str:
        """
        为复合查询生成提示语，指导 LLM 生成正确的 SQL

        Args:
            question: 用户问题

        Returns:
            str: 复合查询提示语
        """
        # 检测具体类型并生成针对性提示
        if re.search(r'(最高|最大).{0,20}(和|与).{0,20}(最低|最小)', question, re.IGNORECASE) or \
           re.search(r'(最低|最小).{0,20}(和|与).{0,20}(最高|最大)', question, re.IGNORECASE):
            return """
【复合查询提示】这是一个需要同时返回"最高"和"最低"两个结果的查询。
请使用 UNION ALL 组合两个查询：
1. 第一个子查询：使用 ORDER BY ... DESC LIMIT 1 获取最高/最大值
2. 第二个子查询：使用 ORDER BY ... ASC LIMIT 1 获取最低/最小值
3. 添加一个 type 列来区分结果类型（如 '最高' 或 '最低'）

示例结构：
(SELECT ..., '最高' as type FROM ... ORDER BY value DESC LIMIT 1)
UNION ALL
(SELECT ..., '最低' as type FROM ... ORDER BY value ASC LIMIT 1)
"""

        # 检测前N名和后N名
        match = re.search(r'前(\d+).{0,20}(和|与).{0,20}后(\d+)', question, re.IGNORECASE)
        if match:
            top_n = match.group(1)
            bottom_n = match.group(3)
            return f"""
【复合查询提示】这是一个需要同时返回"前{top_n}名"和"后{bottom_n}名"的查询。
请使用 UNION ALL 组合两个查询：
1. 第一个子查询：使用 ORDER BY ... DESC LIMIT {top_n} 获取前{top_n}名
2. 第二个子查询：使用 ORDER BY ... ASC LIMIT {bottom_n} 获取后{bottom_n}名
3. 添加一个 type 列来区分结果类型（如 'TOP{top_n}' 或 'BOTTOM{bottom_n}'）
"""

        # 通用复合查询提示
        return """
【复合查询提示】这是一个复合查询，需要返回多个不同条件的结果。
请确保使用 UNION ALL 或子查询来完整回答用户的所有需求，不要只返回部分结果。
"""

    @staticmethod
    def _validate_result_completeness(question: str, df: pd.DataFrame) -> tuple:
        """
        验证结果是否完整回答了问题

        Args:
            question: 用户问题
            df: 查询结果 DataFrame

        Returns:
            tuple: (is_complete, suggestion) 是否完整以及不完整时的建议
        """
        # 检测"最高和最低"类型查询
        if re.search(r'(最高|最大).{0,20}(和|与).{0,20}(最低|最小)', question, re.IGNORECASE) or \
           re.search(r'(最低|最小).{0,20}(和|与).{0,20}(最高|最大)', question, re.IGNORECASE):
            if len(df) < 2:
                return False, "查询结果可能不完整。您的问题同时询问了最高和最低值，但只返回了一条记录。您可以追问：'请同时给出最高和最低的结果'"

        # 检测"前N名和后N名"类型查询
        match = re.search(r'前(\d+).{0,20}(和|与).{0,20}后(\d+)', question, re.IGNORECASE)
        if match:
            top_n = int(match.group(1))
            bottom_n = int(match.group(3))
            expected = top_n + bottom_n
            if len(df) < expected:
                return False, f"查询结果可能不完整。您期望获取前{top_n}名和后{bottom_n}名共{expected}条记录，但只返回了{len(df)}条。"

        return True, ""

    @classmethod
    async def generate_result(
        cls, 
        dataset_id: int, 
        question: str, 
        db_session: Session, 
        use_cache: bool = True,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        data_table_id: Optional[int] = None
    ):
        """
        Generate SQL and execute it with intelligent multi-round dialogue (Auto-Reflection Loop).
        Now with Redis-based query caching and context-aware query rewriting.

        Features:
        1. Redis-based SQL caching with 24-hour TTL
        2. Context-aware query rewriting for multi-turn conversations
        3. LLM-driven intermediate SQL detection and execution
        4. Intelligent clarification generation when ambiguous
        5. Graceful text-only responses (no exceptions for non-SQL)
        6. LLM-powered friendly error messages on failures
        7. All responses in Chinese

        Args:
            dataset_id: Dataset ID
            question: User's question
            db_session: Database session
            use_cache: Whether to use cache (default: True)
            conversation_history: Conversation history for context understanding

        Returns:
            dict: Result with sql, columns, rows, chart_type, etc.
                  Includes 'is_cached' flag when result is from cache
        """
        # 延迟导入避免循环依赖
        from app.services.vanna.analyst_service import VannaAnalystService

        execution_steps = []
        start_time = time.perf_counter()
        
        # === Step 0: Query Rewriting (if needed) ===
        original_question = question
        if conversation_history and QueryRewriter.should_rewrite(question, conversation_history):
            try:
                execution_steps.append("检测到省略查询，正在补全...")
                question = QueryRewriter.rewrite_query(question, conversation_history)
                execution_steps.append(f"查询已补全：{question}")
                logger.info(
                    "Query rewritten",
                    original=original_question,
                    rewritten=question,
                    dataset_id=dataset_id
                )
            except Exception as e:
                logger.warning(f"Query rewriting failed: {e}")
                execution_steps.append("查询补全失败，使用原始查询")

        # 如果指定了数据表，增强问题提示并限制查询范围
        enhanced_question = question
        table_constraint = ""
        target_table_name = None
        
        if data_table_id:
            try:
                from app.models.metadata import DataTable
                data_table = db_session.query(DataTable).filter(DataTable.id == data_table_id).first()
                if data_table:
                    target_table_name = data_table.physical_table_name
                    table_constraint = f"\n\n【重要提示】此查询必须且只能使用表: {target_table_name}。不要使用其他任何表，不要进行 JOIN 操作。"
                    enhanced_question = f"{question}{table_constraint}"
                    execution_steps.append(f"查询限制在表: {target_table_name}")
                    logger.info(
                        "Query restricted to specific table",
                        dataset_id=dataset_id,
                        data_table_id=data_table_id,
                        table_name=target_table_name
                    )
            except Exception as e:
                logger.warning(f"Failed to load data table info: {e}")

        # === 复合查询检测与提示增强 ===
        is_compound_query = cls._detect_compound_query(question)
        compound_hint = ""
        if is_compound_query:
            compound_hint = cls._get_compound_query_hint(question)
            enhanced_question = enhanced_question + compound_hint
            execution_steps.append("检测到复合查询，已增强 Prompt 提示")
            logger.info(
                "Compound query detected",
                dataset_id=dataset_id,
                question=question[:100]
            )

        # 记录请求开始
        logger.info(
            "SQL generation started",
            dataset_id=dataset_id,
            question=question[:100],
            question_length=len(question),
            use_cache=use_cache,
            data_table_id=data_table_id
        )

        # === Step 0: SQL Cache Check ===
        if use_cache:
            cache_check_start = time.perf_counter()

            try:
                cached_sql = await VannaCacheService.get_cached_sql(dataset_id, question)
                if cached_sql:
                    cache_check_time = (time.perf_counter() - cache_check_start) * 1000
                    logger.info(
                        "SQL cache hit",
                        dataset_id=dataset_id,
                        cache_check_time_ms=round(cache_check_time, 2)
                    )
                    execution_steps.append("SQL缓存命中")

                    # 关键点：拿到缓存的 SQL 后，重新执行查询获取最新数据
                    try:
                        stmt = select(Dataset).options(selectinload(Dataset.datasource)).where(Dataset.id == dataset_id)
                        result = db_session.execute(stmt)
                        dataset = result.scalars().first()

                        if not dataset or not dataset.datasource:
                            logger.warning(
                                "缓存失效",
                                dataset_id=dataset_id,
                                reason="dataset or datasource not found"
                            )
                            await VannaCacheService.delete_cached_sql(dataset_id, question)
                            execution_steps.append("缓存已失效，进入常规流程")
                        else:
                            # 重新执行 SQL 查询
                            sql_exec_start = time.perf_counter()
                            df = cls._execute_sql(dataset, cached_sql)
                            sql_exec_time = (time.perf_counter() - sql_exec_start) * 1000

                            logger.info(
                                "SQL executed from cache",
                                dataset_id=dataset_id,
                                sql=cached_sql[:200],
                                row_count=len(df),
                                sql_exec_time_ms=round(sql_exec_time, 2)
                            )
                            execution_steps.append(f"重新执行查询，返回 {len(df)} 行")

                            # 推断图表类型
                            chart_type = utils.infer_chart_type(df)

                            # 序列化数据
                            cleaned_rows = utils.serialize_dataframe(df)

                            # 生成业务分析
                            insight = None
                            data_interpretation = None
                            fluctuation_analysis = None
                            
                            if len(df) > 0:
                                try:
                                    execution_steps.append("正在生成业务分析...")
                                    insight = VannaAnalystService.generate_data_insight(
                                        question=question,
                                        sql=cached_sql,
                                        df=df,
                                        dataset_id=dataset_id
                                    )
                                    execution_steps.append("业务分析生成完成")
                                except Exception as insight_error:
                                    logger.warning("业务分析生成失败", dataset_id=dataset_id, error=str(insight_error))
                                    execution_steps.append("业务分析生成失败")
                                
                                # Generate Data Interpretation
                                try:
                                    from app.services.data_insight import DataInsightAnalyzer
                                    execution_steps.append("正在进行数据解读...")
                                    data_interpretation = await DataInsightAnalyzer.analyze_data(
                                        df=df,
                                        question=question,
                                        dataset_id=dataset_id
                                    )
                                    execution_steps.append("数据解读完成")
                                except Exception as di_error:
                                    logger.warning(f"Failed to generate data interpretation: {di_error}")
                                    execution_steps.append("数据解读失败")
                                
                                # Generate Fluctuation Analysis
                                try:
                                    from app.services.fluctuation_analyzer import FluctuationAnalyzer
                                    execution_steps.append("正在分析数据波动...")
                                    fluctuation_analysis = await FluctuationAnalyzer.analyze_fluctuation(
                                        df=df,
                                        question=question,
                                        dataset_id=dataset_id
                                    )
                                    if fluctuation_analysis and fluctuation_analysis.get("has_fluctuation"):
                                        execution_steps.append("波动归因分析完成")
                                    else:
                                        execution_steps.append("未检测到显著波动")
                                except Exception as fa_error:
                                    logger.warning(f"Failed to generate fluctuation analysis: {fa_error}")
                                    execution_steps.append("波动分析失败")

                            # Generate Followup Questions (后续推荐问题)
                            followup_questions = None
                            if len(df) > 0:
                                try:
                                    execution_steps.append("正在生成后续推荐问题...")
                                    followup_questions = await VannaAnalystService.generate_followup_questions(
                                        current_question=question,
                                        current_result={
                                            "sql": cached_sql,
                                            "columns": df.columns.tolist(),
                                            "rows": cleaned_rows,
                                            "chart_type": chart_type,
                                            "data_interpretation": data_interpretation,
                                            "fluctuation_analysis": fluctuation_analysis
                                        },
                                        dataset_id=dataset_id,
                                        db_session=db_session,
                                        limit=3
                                    )
                                    execution_steps.append(f"生成了 {len(followup_questions)} 个后续问题")
                                except Exception as fq_error:
                                    logger.warning(f"Failed to generate followup questions: {fq_error}")
                                    execution_steps.append("后续问题生成失败")
                            
                            total_time = (time.perf_counter() - start_time) * 1000
                            logger.info(
                                "Request completed (from cache)",
                                dataset_id=dataset_id,
                                total_time_ms=round(total_time, 2),
                                from_cache=True
                            )

                            return {
                                "sql": cached_sql,
                                "columns": df.columns.tolist(),
                                "rows": cleaned_rows,
                                "chart_type": chart_type,
                                "summary": None,
                                "steps": execution_steps,
                                "is_cached": True,
                                "from_cache": True,
                                "insight": insight,
                                "data_interpretation": data_interpretation,
                                "fluctuation_analysis": fluctuation_analysis,
                                "followup_questions": followup_questions
                            }
                    except Exception as e:
                        logger.warning(
                            "缓存 SQL 执行失败",
                            dataset_id=dataset_id,
                            error=str(e)[:200],
                            cached_sql=cached_sql[:100]
                        )
                        execution_steps.append(f"缓存 SQL 执行失败: {str(e)[:50]}，进入常规流程")
                        await VannaCacheService.delete_cached_sql(dataset_id, question)
                else:
                    logger.debug("缓存未命中", dataset_id=dataset_id)
                    execution_steps.append("SQL缓存未命中")
            except Exception as e:
                logger.warning(f"SQL cache read failed: {e}. Proceeding without cache.")
                execution_steps.append(f"SQL缓存读取失败: {str(e)[:50]}")

        try:
            # === Step A: Initial Setup ===
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

            # Get Vanna instance and database engine
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            engine = DBInspector.get_engine(dataset.datasource)

            execution_steps.append("初始化完成")

            # === Step B: Initial Generation ===
            llm_gen_start = time.perf_counter()
            try:
                # 使用增强后的问题（如果有表约束）
                query_text = enhanced_question + " (请用中文回答)"
                llm_response = vn.generate_sql(query_text)
                llm_gen_time = (time.perf_counter() - llm_gen_start) * 1000

                logger.info(
                    "LLM SQL generation completed",
                    dataset_id=dataset_id,
                    llm_gen_time_ms=round(llm_gen_time, 2),
                    response_length=len(llm_response)
                )
                execution_steps.append("LLM 初始响应生成")
            except Exception as e:
                llm_gen_time = (time.perf_counter() - llm_gen_start) * 1000
                logger.error(
                    "LLM generation failed",
                    dataset_id=dataset_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    llm_gen_time_ms=round(llm_gen_time, 2),
                    exc_info=True
                )
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
            max_rounds = 3
            current_response = llm_response

            for round_num in range(1, max_rounds + 1):
                execution_steps.append(f"第 {round_num} 轮处理")
                logger.info(f"Round {round_num}: Processing response")

                # === Situation 1: Intermediate SQL ===
                intermediate_sql = utils.extract_intermediate_sql(current_response)

                if intermediate_sql:
                    execution_steps.append(f"检测到中间 SQL: {intermediate_sql[:100]}")
                    logger.info(
                        "Intermediate SQL detected",
                        dataset_id=dataset_id,
                        round_num=round_num,
                        intermediate_sql=intermediate_sql[:200]
                    )

                    try:
                        intermediate_exec_start = time.perf_counter()
                        # 转义SQL中的%符号
                        escaped_intermediate_sql = intermediate_sql.replace('%', '%%')
                        df_intermediate = cls._execute_sql(dataset, intermediate_sql)
                        intermediate_exec_time = (time.perf_counter() - intermediate_exec_start) * 1000

                        logger.info(
                            "Intermediate SQL executed",
                            dataset_id=dataset_id,
                            row_count=len(df_intermediate),
                            exec_time_ms=round(intermediate_exec_time, 2)
                        )
                        execution_steps.append(f"中间 SQL 执行成功，获取 {len(df_intermediate)} 行")

                        values = []
                        if not df_intermediate.empty:
                            values = df_intermediate.iloc[:, 0].tolist()
                            values = [str(v) for v in values if v is not None]

                        execution_steps.append(f"中间值: {values}")

                        reflection_prompt = f"""用户的问题是: {question}

我执行了中间查询，数据库中存在的相关值为: {values}

请根据这些值:
1. 如果能确定用户意图，请生成最终 SQL 查询(只输出 SQL，不要解释)。
2. 如果不能确定(例如用户问'大客户'但数据库只有'VIP'和'普通')，请用**中文**生成一个澄清问题，询问用户指的是哪一个值。

请直接输出 SQL 或澄清问题，不要额外解释。"""

                        execution_steps.append("LLM 二次推理")
                        current_response = vn.submit_prompt(reflection_prompt)
                        continue

                    except Exception as e:
                        logger.warning(f"Intermediate SQL execution failed: {e}")
                        execution_steps.append(f"中间 SQL 执行失败: {str(e)[:100]}")

                # === Situation 2: Pure Text (Clarification/Refusal) ===
                try:
                    cleaned_sql = utils.clean_sql(current_response)
                    is_sql = utils.is_valid_sql(cleaned_sql)
                except:
                    is_sql = False
                    cleaned_sql = ""

                if not is_sql:
                    execution_steps.append("LLM 返回纯文本(澄清/说明)")
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
                
                # 如果指定了数据表，验证 SQL 是否只查询该表
                if target_table_name:
                    sql_upper = cleaned_sql.upper()
                    table_name_upper = target_table_name.upper()
                    
                    # 检查 SQL 是否包含目标表
                    if table_name_upper not in sql_upper:
                        execution_steps.append(f"⚠️ SQL 未使用指定的表 {target_table_name}，需要修正")
                        
                        # 尝试用 LLM 修正
                        correction_prompt = f"""用户要求只查询表 {target_table_name}，但生成的 SQL 没有使用该表。
                        
原始问题: {question}
错误的 SQL: {cleaned_sql}

请生成一个新的 SQL，确保：
1. 只使用表 {target_table_name}
2. 不要使用其他表
3. 不要进行 JOIN 操作
4. 回答用户的原始问题

只输出修正后的 SQL，不要解释。"""
                        
                        try:
                            current_response = vn.submit_prompt(correction_prompt)
                            execution_steps.append("LLM 已生成修正方案")
                            continue
                        except Exception as e:
                            logger.error(f"Failed to correct SQL for table constraint: {e}")
                    else:
                        # 检查是否使用了其他表（简单检测）
                        from_match = re.search(r'FROM\s+(\w+)', sql_upper)
                        if from_match:
                            used_table = from_match.group(1)
                            if used_table != table_name_upper:
                                execution_steps.append(f"⚠️ SQL 使用了错误的表 {used_table}，应使用 {target_table_name}")
                                # 尝试简单替换
                                cleaned_sql = re.sub(
                                    r'\bFROM\s+\w+\b',
                                    f'FROM {target_table_name}',
                                    cleaned_sql,
                                    flags=re.IGNORECASE
                                )
                                execution_steps.append(f"已自动替换为 {target_table_name}")

                # 添加LIMIT子句防止查询过多数据导致超时
                sql_upper = cleaned_sql.upper()
                has_limit = 'LIMIT' in sql_upper

                if not has_limit:
                    cleaned_sql = cleaned_sql.rstrip(';').strip() + ' LIMIT 1000'
                    execution_steps.append("自动添加 LIMIT 1000 防止过多数据")
                elif has_limit:
                    limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
                    if limit_match:
                        limit_value = int(limit_match.group(1))
                        if limit_value > 5000:
                            cleaned_sql = re.sub(r'LIMIT\s+\d+', 'LIMIT 1000', cleaned_sql, flags=re.IGNORECASE)
                            execution_steps.append(f"将 LIMIT {limit_value} 调整为 LIMIT 1000 防止超时")

                try:
                    final_exec_start = time.perf_counter()
                    # 转义SQL中的%符号，防止pymysql将其视为参数占位符
                    # 例如：DATE_FORMAT(..., '%Y-%m') 需要转义为 DATE_FORMAT(..., '%%Y-%%m')
                    escaped_sql = cleaned_sql.replace('%', '%%')
                    df = cls._execute_sql(dataset, escaped_sql)
                    final_exec_time = (time.perf_counter() - final_exec_start) * 1000

                    logger.info(
                        "SQL executed successfully",
                        dataset_id=dataset_id,
                        sql=cleaned_sql[:200],
                        row_count=len(df),
                        column_count=len(df.columns),
                        sql_exec_time_ms=round(final_exec_time, 2)
                    )
                    execution_steps.append(f"SQL 执行成功，返回 {len(df)} 行")

                    # 使用智能图表推荐器
                    chart_type = ChartRecommender.recommend(df, question)
                    execution_steps.append(f"智能推荐图表类型: {chart_type}")
                    
                    # 获取备用图表类型
                    alternative_charts = ChartRecommender.get_alternative_charts(df, chart_type)

                    cleaned_rows = utils.serialize_dataframe(df)

                    # Generate Business Insight
                    insight = None
                    data_interpretation = None
                    fluctuation_analysis = None
                    followup_questions = None  # 在外部初始化，确保所有代码路径都能访问
                    
                    if len(df) > 0:
                        try:
                            execution_steps.append("正在生成业务分析...")
                            insight = VannaAnalystService.generate_data_insight(
                                question=question,
                                sql=cleaned_sql,
                                df=df,
                                dataset_id=dataset_id
                            )
                            execution_steps.append("业务分析生成完成")
                        except Exception as insight_error:
                            logger.warning(f"Failed to generate insight: {insight_error}")
                            execution_steps.append("业务分析生成失败")
                        
                        # Generate Data Interpretation (并行执行以提高性能)
                        try:
                            from app.services.data_insight import DataInsightAnalyzer
                            execution_steps.append("正在进行数据解读...")
                            data_interpretation = await DataInsightAnalyzer.analyze_data(
                                df=df,
                                question=question,
                                dataset_id=dataset_id
                            )
                            execution_steps.append("数据解读完成")
                        except Exception as di_error:
                            logger.warning(f"Failed to generate data interpretation: {di_error}")
                            execution_steps.append("数据解读失败")
                        
                        # Generate Fluctuation Analysis
                        try:
                            from app.services.fluctuation_analyzer import FluctuationAnalyzer
                            execution_steps.append("正在分析数据波动...")
                            fluctuation_analysis = await FluctuationAnalyzer.analyze_fluctuation(
                                df=df,
                                question=question,
                                dataset_id=dataset_id
                            )
                            if fluctuation_analysis and fluctuation_analysis.get("has_fluctuation"):
                                execution_steps.append("波动归因分析完成")
                            else:
                                execution_steps.append("未检测到显著波动")
                        except Exception as fa_error:
                            logger.warning(f"Failed to generate fluctuation analysis: {fa_error}")
                            execution_steps.append("波动分析失败")
                        
                        # Generate Followup Questions (后续推荐问题)
                        try:
                            execution_steps.append("正在生成后续推荐问题...")
                            followup_questions = await VannaAnalystService.generate_followup_questions(
                                current_question=question,
                                current_result={
                                    "sql": cleaned_sql,
                                    "columns": df.columns.tolist(),
                                    "rows": cleaned_rows,
                                    "chart_type": chart_type,
                                    "data_interpretation": data_interpretation,
                                    "fluctuation_analysis": fluctuation_analysis
                                },
                                dataset_id=dataset_id,
                                db_session=db_session,
                                limit=3
                            )
                            execution_steps.append(f"生成了 {len(followup_questions)} 个后续问题")
                        except Exception as fq_error:
                            logger.warning(f"Failed to generate followup questions: {fq_error}")
                            execution_steps.append("后续问题生成失败")

                    # === 结果完整性验证 ===
                    result_warning = None
                    if is_compound_query:
                        is_complete, suggestion = cls._validate_result_completeness(question, df)
                        if not is_complete:
                            result_warning = suggestion
                            execution_steps.append(f"⚠️ {suggestion}")
                            logger.warning(
                                "Incomplete result for compound query",
                                dataset_id=dataset_id,
                                question=question[:100],
                                row_count=len(df)
                            )

                    result = {
                        "sql": cleaned_sql,
                        "columns": df.columns.tolist(),
                        "rows": cleaned_rows,
                        "chart_type": chart_type,
                        "alternative_charts": alternative_charts,
                        "summary": None,
                        "steps": execution_steps,
                        "from_cache": False,
                        "insight": insight,
                        "data_interpretation": data_interpretation,
                        "fluctuation_analysis": fluctuation_analysis,
                        "followup_questions": followup_questions,
                        "result_warning": result_warning  # 新增：结果不完整时的警告信息
                    }

                    # === Step D: Write to Cache ===
                    if use_cache:
                        try:
                            await VannaCacheService.cache_sql(dataset_id, question, cleaned_sql)
                            execution_steps.append("SQL已缓存 (TTL: 24h)")
                        except Exception as e:
                            logger.warning("缓存写入失败", dataset_id=dataset_id, error=str(e))
                            execution_steps.append(f"SQL缓存写入失败: {str(e)[:50]}")

                    total_time = (time.perf_counter() - start_time) * 1000
                    logger.info(
                        "Request completed",
                        dataset_id=dataset_id,
                        total_time_ms=round(total_time, 2),
                        from_cache=False
                    )

                    return result

                except Exception as e:
                    error_msg = str(e)
                    logger.error(
                        "SQL execution failed",
                        dataset_id=dataset_id,
                        sql=cleaned_sql[:200],
                        error=error_msg[:200],
                        error_type=type(e).__name__,
                        exc_info=True
                    )
                    execution_steps.append(f"SQL 执行失败: {error_msg[:100]}")

                    # 检查是否是连接超时错误
                    is_timeout_error = '2013' in error_msg or 'Lost connection' in error_msg or 'timeout' in error_msg.lower()
                    
                    # 检查是否是列不存在错误
                    is_column_error = '1054' in error_msg or 'Unknown column' in error_msg or "doesn't exist" in error_msg

                    # 处理列不存在错误 - 提供真实表结构信息给LLM
                    if is_column_error and round_num < max_rounds:
                        try:
                            execution_steps.append("检测到列不存在错误，尝试获取真实表结构")
                            
                            # 提取SQL中涉及的表名
                            table_names = set()
                            # 匹配 FROM 和 JOIN 后面的表名
                            from_match = re.findall(r'\bFROM\s+`?(\w+)`?', cleaned_sql, re.IGNORECASE)
                            join_match = re.findall(r'\bJOIN\s+`?(\w+)`?', cleaned_sql, re.IGNORECASE)
                            table_names.update(from_match)
                            table_names.update(join_match)
                            
                            if table_names:
                                # 获取所有涉及表的真实列信息
                                table_schemas = {}
                                for table in table_names:
                                    try:
                                        columns = DBInspector.get_column_names(dataset.datasource, table)
                                        table_schemas[table] = columns
                                        execution_steps.append(f"获取表 {table} 的列: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}")
                                    except Exception as col_err:
                                        logger.warning(f"Failed to get columns for table {table}: {col_err}")
                                        
                                if table_schemas:
                                    # 构建详细的表结构信息
                                    schema_info = "\n\n".join([
                                        f"表 {table} 的实际字段:\n{', '.join(cols)}"
                                        for table, cols in table_schemas.items()
                                    ])
                                    
                                    correction_prompt = f"""以下 SQL 在 {dataset.datasource.type.upper()} 数据库上执行失败:

SQL:
{cleaned_sql}

错误:
{error_msg}

{schema_info}

【重要】请根据表的实际字段修正这个 SQL。
- 只能使用上面列出的字段，不要使用不存在的字段
- 如果用户问的字段不存在，请基于现有字段生成最接近的查询
- 用户的原始问题是：{question}

只输出修正后的 SQL，不要解释。"""
                                    
                                    current_response = vn.submit_prompt(correction_prompt)
                                    execution_steps.append("LLM 已基于真实表结构生成修正方案")
                                    continue
                        except Exception as schema_err:
                            logger.error(f"Failed to get table schema for correction: {schema_err}")
                            execution_steps.append(f"获取表结构失败: {str(schema_err)[:50]}")
                    
                    if is_timeout_error:
                        error_prompt = f"""查询执行超时了。用户的问题是: {question}

请用中文礼貌地告诉用户：
1. 查询耗时过长，可能是数据量较大
2. 建议缩小时间范围，比如改为"最近 7 天"或"本周"
3. 或者添加更具体的筛选条件

保持简洁友好，不要提及技术细节。"""
                        try:
                            friendly_msg = vn.submit_prompt(error_prompt)
                            execution_steps.append("检测到超时，生成优化建议")
                        except:
                            friendly_msg = "抱歉，查询耗时过长。建议您缩小时间范围（比如改为'最近 7 天'或'本周'），或者添加更具体的筛选条件。"

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
                            execution_steps.append("LLM 已生成修正方案")
                            continue

                        except Exception as correction_error:
                            logger.error(f"SQL correction failed: {correction_error}")
                            execution_steps.append(f"修正过程出错: {str(correction_error)[:100]}")

                    # Last round or correction failed
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
                        friendly_msg = "抱歉，查询执行遇到了问题。建议您换一种方式描述问题，或者提供更多相关信息。"

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

            try:
                vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
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
