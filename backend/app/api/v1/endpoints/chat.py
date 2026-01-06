from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from app.services.vanna_manager import VannaManager

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with the dataset to generate SQL and results.
    """
    try:
        result = await VannaManager.generate_result(
            dataset_id=request.dataset_id,
            question=request.question,
            db_session=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log unexpected errors?
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit user feedback on AI-generated SQL.
    Positive feedback (rating=1) trains the AI with the correct Q-SQL pair.
    Negative feedback (rating=-1) with corrected SQL also trains the AI.
    
    Args:
        request: Feedback request containing dataset_id, question, sql, and rating
        db: Database session
    
    Returns:
        FeedbackResponse with success status and message
    """
    try:
        # Only train on positive feedback or corrected SQL
        if request.rating == 1:
            # User likes this result - train it
            VannaManager.train_qa(
                dataset_id=request.dataset_id,
                question=request.question,
                sql=request.sql,
                db_session=db
            )
            return FeedbackResponse(
                success=True,
                message="感谢反馈！AI 已记住这个查询逻辑。"
            )
        elif request.rating == -1:
            # User provided corrected SQL - train it
            VannaManager.train_qa(
                dataset_id=request.dataset_id,
                question=request.question,
                sql=request.sql,  # This should be the corrected SQL
                db_session=db
            )
            return FeedbackResponse(
                success=True,
                message="感谢你的修正！AI 已学习了正确的 SQL。"
            )
        else:
            return FeedbackResponse(
                success=False,
                message="无效的评分值，应为 1 或 -1。"
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"反馈提交失败: {str(e)}")
