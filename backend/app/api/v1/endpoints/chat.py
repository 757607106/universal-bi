from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from app.db.session import get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import User, Dataset
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, SummaryRequest, SummaryResponse
from app.services.vanna_manager import VannaManager
from app.core.logger import get_logger

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
        result = await VannaManager.generate_result(
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
        raise HTTPException(status_code=500, detail=str(e))

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
            VannaManager.train_qa(
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
            VannaManager.train_qa(
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
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")

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
        summary = VannaManager.generate_summary(
            question=request.question,
            df=df,
            dataset_id=request.dataset_id
        )
        
        return SummaryResponse(summary=summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"总结生成失败: {str(e)}")
