from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
import pandas as pd
import json
import uuid

from app.db.session import get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import User, Dataset
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, SummaryRequest, SummaryResponse
from app.services.vanna import VannaSqlGenerator, VannaAnalystService, VannaTrainingService
from app.services.vanna_manager import VannaAgentManager
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
            use_cache=request.use_cache  # 传递缓存控制参数
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
