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

    @classmethod
    async def generate_result(
        cls, 
        dataset_id: int, 
        question: str, 
        db_session: Session, 
        use_cache: bool = True,
        conversation_history: Optional[List[Dict[str, str]]] = None
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

        # 记录请求开始
        logger.info(
            "SQL generation started",
            dataset_id=dataset_id,
            question=question[:100],
            question_length=len(question),
            use_cache=use_cache
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
                            engine = DBInspector.get_engine(dataset.datasource)
                            # 转义SQL中的%符号
                            escaped_cached_sql = cached_sql.replace('%', '%%')
                            df = pd.read_sql(escaped_cached_sql, engine)
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
                                "insight": insight
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
                llm_response = vn.generate_sql(question + " (请用中文回答)")
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
                        df_intermediate = pd.read_sql(escaped_intermediate_sql, engine)
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
                    df = pd.read_sql(escaped_sql, engine)
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

                    result = {
                        "sql": cleaned_sql,
                        "columns": df.columns.tolist(),
                        "rows": cleaned_rows,
                        "chart_type": chart_type,
                        "alternative_charts": alternative_charts,
                        "summary": None,
                        "steps": execution_steps,
                        "from_cache": False,
                        "insight": insight
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
