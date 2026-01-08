from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session, selectinload
import pandas as pd
import json
import uuid

from app.db.session import get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import User, Dataset
from app.schemas.chat import (
    ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, 
    SummaryRequest, SummaryResponse, InputSuggestRequest, InputSuggestResponse,
    FollowupSuggestRequest, FollowupSuggestResponse, ExportRequest
)
from app.services.vanna import VannaSqlGenerator, VannaAnalystService, VannaTrainingService
from app.services.vanna_manager import VannaAgentManager
from app.services.data_exporter import DataExporter
from app.services.input_suggester import InputSuggester
from app.services.enhanced_exporter import EnhancedExporter
from app.core.logger import get_logger
from app.core.config import settings

router = APIRouter()
logger = get_logger(__name__)

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the dataset to generate SQL and results.
    应用数据隔离：需要验证 Dataset 的访问权
    """
    # 记录用户提问事件
    logger.info(
        "Chat request received",
        user_id=current_user.id,
        user_email=current_user.email,
        dataset_id=request.dataset_id,
        question_length=len(request.question),
        use_cache=request.use_cache
    )
    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        logger.warning(
            "Dataset access denied",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            reason="not found or access denied"
        )
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        result = await VannaSqlGenerator.generate_result(
            dataset_id=request.dataset_id,
            question=request.question,
            db_session=db,
            use_cache=request.use_cache,  # 传递缓存控制参数
            conversation_history=request.conversation_history,  # 传递对话历史
            data_table_id=request.data_table_id  # 传递数据表ID
        )
        
        logger.info(
            "Chat request completed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            has_sql=result.get('sql') is not None,
            chart_type=result.get('chart_type'),
            row_count=len(result.get('rows', [])) if result.get('rows') else 0
        )
        
        return result
    except ValueError as e:
        logger.error(
            "Invalid request parameters",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Chat request failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        # 生产环境不暴露详细错误信息
        error_detail = str(e) if settings.DEV else "处理请求时发生内部错误，请稍后重试"
        raise HTTPException(status_code=500, detail=error_detail)

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit user feedback on AI-generated SQL.
    Positive feedback (rating=1) trains the AI with the correct Q-SQL pair.
    Negative feedback (rating=-1) with corrected SQL also trains the AI.
    应用数据隔离：需要验证 Dataset 的访问权
    
    Args:
        request: Feedback request containing dataset_id, question, sql, and rating
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        FeedbackResponse with success status and message
    """
    # 记录反馈请求
    logger.info(
        "User feedback received",
        user_id=current_user.id,
        dataset_id=request.dataset_id,
        rating=request.rating,
        has_corrected_sql=bool(request.sql)
    )
    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以训练
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot train public resources")
    
    try:
        # Only train on positive feedback or corrected SQL
        if request.rating == 1:
            # User likes this result - train with original SQL
            VannaTrainingService.train_qa(
                dataset_id=request.dataset_id,
                question=request.question,
                sql=request.sql,
                db_session=db
            )
            logger.info(
                "Positive feedback trained",
                user_id=current_user.id,
                dataset_id=request.dataset_id
            )
            return FeedbackResponse(
                success=True,
                message="感谢反馈！AI 已记住这个查询逻辑。"
            )
        elif request.rating == -1:
            # User dislikes result and provided corrected SQL
            # The 'sql' field contains the corrected SQL in this case
            VannaTrainingService.train_qa(
                dataset_id=request.dataset_id,
                question=request.question,
                sql=request.sql,  # This is the corrected SQL from user
                db_session=db
            )
            logger.info(
                "Negative feedback trained with corrected SQL",
                user_id=current_user.id,
                dataset_id=request.dataset_id
            )
            return FeedbackResponse(
                success=True,
                message="感谢你的修正！AI 已学习了正确的 SQL。"
            )
        else:
            logger.warning(
                "Invalid rating value",
                user_id=current_user.id,
                dataset_id=request.dataset_id,
                rating=request.rating
            )
            return FeedbackResponse(
                success=False,
                message="无效的评分值，应为 1 或 -1。"
            )
    except ValueError as e:
        logger.error(
            "Feedback training failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Feedback submission failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        # 生产环境不暴露详细错误信息
        error_detail = f"反馈提交失败: {str(e)}" if settings.DEV else "反馈提交失败，请稍后重试"
        raise HTTPException(status_code=500, detail=error_detail)

@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-powered business summary of query results.
    This is a separate endpoint to avoid blocking the main chat response.
    应用数据隔离：需要验证 Dataset 的访问权
    
    Args:
        request: Summary request containing dataset_id, question, sql, and chart_data
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        SummaryResponse with AI-generated summary text
    """
    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        # Convert rows to DataFrame
        df = pd.DataFrame(request.rows)
        
        # Generate summary
        summary = VannaAnalystService.generate_summary(
            question=request.question,
            df=df,
            dataset_id=request.dataset_id
        )
        
        return SummaryResponse(summary=summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 生产环境不暴露详细错误信息
        error_detail = f"总结生成失败: {str(e)}" if settings.DEV else "总结生成失败，请稍后重试"
        raise HTTPException(status_code=500, detail=error_detail)


# =============================================================================
# Vanna 2.0 Agent API 端点 (新增)
# =============================================================================

@router.post("/agent")
async def agent_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用 Vanna 2.0 Agent 进行对话式查询（流式响应）

    与 `/chat` 端点的区别：
    - 使用 Agent API 而非 Legacy API
    - 支持流式响应 (Server-Sent Events)
    - 工具调用机制 (SQL 生成 + SQL 执行)
    - 更丰富的上下文增强

    Response Content-Type: application/x-ndjson (Newline Delimited JSON)

    每行是一个 JSON 对象，格式如下：
    {"type": "ComponentType", "data": {...}}
    """
    # 记录请求
    logger.info(
        "Agent chat request received",
        user_id=current_user.id,
        user_email=current_user.email,
        dataset_id=request.dataset_id,
        question_length=len(request.question)
    )

    # 验证 Dataset 访问权限（带 datasource eager loading）
    ds_query = db.query(Dataset).options(
        selectinload(Dataset.datasource)
    ).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()

    if not dataset:
        logger.warning(
            "Dataset access denied",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            reason="not found or access denied"
        )
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")

    if not dataset.datasource:
        raise HTTPException(status_code=400, detail="Dataset has no datasource configured")

    async def generate_stream():
        """生成流式响应"""
        try:
            async for component in VannaAgentManager.chat(
                dataset_id=request.dataset_id,
                question=request.question,
                user_id=str(current_user.id),
                datasource=dataset.datasource,
                conversation_id=request.conversation_id if hasattr(request, 'conversation_id') else None
            ):
                # 序列化组件
                component_data = {
                    "type": component.__class__.__name__
                }

                # 提取组件属性
                if hasattr(component, 'text'):
                    component_data["text"] = component.text
                if hasattr(component, 'content'):
                    component_data["content"] = component.content
                if hasattr(component, 'markdown'):
                    component_data["markdown"] = component.markdown
                if hasattr(component, 'metadata'):
                    component_data["metadata"] = component.metadata
                if hasattr(component, 'to_dict'):
                    try:
                        component_data["data"] = component.to_dict()
                    except:
                        pass

                # 输出 NDJSON 格式
                yield json.dumps(component_data, ensure_ascii=False) + "\n"

        except Exception as e:
            logger.error(
                "Agent chat stream failed",
                user_id=current_user.id,
                dataset_id=request.dataset_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            # 输出错误消息（流式响应中不区分环境，因为已经在返回数据）
            error_text = str(e)[:100] if settings.DEV else "处理请求时发生错误"
            error_component = {
                "type": "Error",
                "text": f"处理请求时发生错误: {error_text}",
                "error": True
            }
            yield json.dumps(error_component, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.post("/agent/simple")
async def agent_chat_simple(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用 Vanna 2.0 Agent 进行对话式查询（非流式，返回完整响应）

    适用于不需要流式响应的场景，返回结构与 `/chat` 类似。
    """
    # 记录请求
    logger.info(
        "Agent chat simple request received",
        user_id=current_user.id,
        dataset_id=request.dataset_id,
        question_length=len(request.question)
    )

    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).options(
        selectinload(Dataset.datasource)
    ).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")

    if not dataset.datasource:
        raise HTTPException(status_code=400, detail="Dataset has no datasource configured")

    try:
        result = await VannaAgentManager.chat_simple(
            dataset_id=request.dataset_id,
            question=request.question,
            user_id=str(current_user.id),
            datasource=dataset.datasource,
            conversation_id=request.conversation_id if hasattr(request, 'conversation_id') else None
        )

        logger.info(
            "Agent chat simple completed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            component_count=len(result.get('components', []))
        )

        return result

    except Exception as e:
        logger.error(
            "Agent chat simple failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        # 生产环境不暴露详细错误信息
        error_detail = f"Agent 查询失败: {str(e)}" if settings.DEV else "Agent 查询失败，请稍后重试"
        raise HTTPException(status_code=500, detail=error_detail)


# =============================================================================
# 数据导出 API (Export)
# =============================================================================

@router.post("/export/excel")
async def export_to_excel(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出查询结果为Excel文件
    
    Args:
        request: {
            "dataset_id": int,
            "question": str,
            "columns": List[str],
            "rows": List[Dict],
            "filename_prefix": str (optional)
        }
        
    Returns:
        StreamingResponse: Excel文件流
    """
    try:
        dataset_id = request.get("dataset_id")
        columns = request.get("columns", [])
        rows = request.get("rows", [])
        question = request.get("question", "分析结果")
        
        # 验证Dataset访问权限
        ds_query = db.query(Dataset).filter(Dataset.id == dataset_id)
        ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
        dataset = ds_query.first()
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found or access denied")
        
        # 生成文件名
        filename = DataExporter.generate_filename(question, "xlsx")
        
        # 导出数据
        excel_bytes, _ = DataExporter.export_to_excel(
            data=rows,
            columns=columns,
            filename_prefix=question[:20]
        )
        
        logger.info(
            "Excel export completed",
            user_id=current_user.id,
            dataset_id=dataset_id,
            row_count=len(rows),
            filename=filename
        )
        
        # 返回文件流
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Excel export failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Excel导出失败: {str(e)}")


@router.post("/export/csv")
async def export_to_csv(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出查询结果为CSV文件
    
    Args:
        request: {
            "dataset_id": int,
            "question": str,
            "columns": List[str],
            "rows": List[Dict],
            "filename_prefix": str (optional)
        }
        
    Returns:
        StreamingResponse: CSV文件流
    """
    try:
        dataset_id = request.get("dataset_id")
        columns = request.get("columns", [])
        rows = request.get("rows", [])
        question = request.get("question", "分析结果")
        
        # 验证Dataset访问权限
        ds_query = db.query(Dataset).filter(Dataset.id == dataset_id)
        ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
        dataset = ds_query.first()
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found or access denied")
        
        # 生成文件名
        filename = DataExporter.generate_filename(question, "csv")
        
        # 导出数据
        csv_bytes, _ = DataExporter.export_to_csv(
            data=rows,
            columns=columns,
            filename_prefix=question[:20]
        )
        
        logger.info(
            "CSV export completed",
            user_id=current_user.id,
            dataset_id=dataset_id,
            row_count=len(rows),
            filename=filename
        )
        
        # 返回文件流
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "CSV export failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"CSV导出失败: {str(e)}")


# =============================================================================
# 输入联想 API 端点
# =============================================================================

@router.post("/suggest-input", response_model=InputSuggestResponse)
async def suggest_input(
    request: InputSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    输入联想 - 基于部分输入实时推荐相关问题
    
    功能特点：
    - 基于用户输入关键词和数据集 schema 生成问题建议
    - 使用 Redis 缓存（5 分钟 TTL）提高响应速度
    - 降级策略：LLM 失败时返回默认建议
    
    Args:
        request: 包含 dataset_id、partial_input 和 limit 的请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        InputSuggestResponse: 包含建议问题列表
    """
    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        logger.warning(
            "Dataset access denied for input suggestion",
            user_id=current_user.id,
            dataset_id=request.dataset_id
        )
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        # 调用输入联想服务
        suggestions = await InputSuggester.suggest_questions(
            dataset_id=request.dataset_id,
            partial_input=request.partial_input,
            db_session=db,
            limit=request.limit
        )
        
        logger.info(
            "Input suggestions generated",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            partial_input=request.partial_input,
            suggestion_count=len(suggestions)
        )
        
        return InputSuggestResponse(suggestions=suggestions)
        
    except Exception as e:
        logger.error(
            "Input suggestion failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e),
            exc_info=True
        )
        # 降级：返回空列表，不影响用户使用
        return InputSuggestResponse(suggestions=[])


# =============================================================================
# 后续推荐问题 API 端点
# =============================================================================

@router.post("/suggest-followup", response_model=FollowupSuggestResponse)
async def suggest_followup(
    request: FollowupSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    后续推荐问题 - 基于当前对话结果推荐后续分析问题（猜你想问）
    
    功能特点：
    - 基于当前问题和查询结果，推荐后续深入分析方向
    - 涵盖维度拆分、对比分析、趋势分析等多个角度
    - 使用 LLM 智能生成，确保问题的相关性和可执行性
    
    Args:
        request: 包含 dataset_id、current_question 和 current_result 的请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        FollowupSuggestResponse: 包含后续问题列表
    """
    # 验证 Dataset 访问权限
    ds_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        logger.warning(
            "Dataset access denied for followup suggestion",
            user_id=current_user.id,
            dataset_id=request.dataset_id
        )
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        # 调用后续问题生成服务
        followup_questions = await VannaAnalystService.generate_followup_questions(
            current_question=request.current_question,
            current_result=request.current_result,
            dataset_id=request.dataset_id,
            db_session=db,
            limit=request.limit
        )
        
        logger.info(
            "Followup questions generated",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            current_question=request.current_question[:50],
            question_count=len(followup_questions)
        )
        
        return FollowupSuggestResponse(followup_questions=followup_questions)
        
    except Exception as e:
        logger.error(
            "Followup suggestion failed",
            user_id=current_user.id,
            dataset_id=request.dataset_id,
            error=str(e),
            exc_info=True
        )
        # 降级：返回空列表
        return FollowupSuggestResponse(followup_questions=[])


# =============================================================================
# 增强导出 API 端点
# =============================================================================

@router.post("/export-result")
async def export_result(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出查询结果（支持多种格式和富内容）
    
    支持的导出格式：
    - excel: Excel 文件（含数据和分析报告）
    - excel_with_chart: Excel 文件（含图表，暂时等同于 excel）
    - pdf: PDF 报告（含数据分析和洞察）
    - csv: CSV 文件（仅数据）
    
    导出内容包括：
    - 查询数据
    - SQL 语句
    - AI 洞察
    - 数据解读
    - 波动归因分析
    
    Args:
        request: 包含问题、数据、分析结果的导出请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        StreamingResponse 或 Response: 文件流
    """
    try:
        # 调用增强导出服务
        file_bytes, filename = await EnhancedExporter.export_with_metadata(
            question=request.question,
            sql=request.sql,
            columns=request.columns,
            rows=request.rows,
            chart_type=request.chart_type,
            chart_data=request.chart_data,
            insight=request.insight,
            data_interpretation=request.data_interpretation,
            fluctuation_analysis=request.fluctuation_analysis,
            export_format=request.format
        )
        
        # 确定 MIME 类型
        if request.format == "pdf":
            media_type = "application/pdf"
        elif request.format == "csv":
            media_type = "text/csv"
        else:  # excel 和 excel_with_chart
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        logger.info(
            "Export completed",
            user_id=current_user.id,
            format=request.format,
            filename=filename,
            size_kb=len(file_bytes) / 1024
        )
        
        # 返回文件流
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except Exception as e:
        logger.error(
            "Export failed",
            user_id=current_user.id,
            format=request.format,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
