from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
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
