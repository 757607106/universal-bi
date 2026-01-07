from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    dataset_id: int
    question: str

class ChatResponse(BaseModel):
    sql: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    chart_type: str
    summary: Optional[str] = None
    answer_text: Optional[str] = None  # For clarification requests
    steps: Optional[List[str]] = None  # Execution steps tracking
    from_cache: Optional[bool] = False  # Whether result is from cache

class SummaryRequest(BaseModel):
    dataset_id: int
    question: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]

class SummaryResponse(BaseModel):
    summary: str

class FeedbackRequest(BaseModel):
    dataset_id: int
    question: str
    sql: str
    rating: int  # 1 for like, -1 for dislike

class FeedbackResponse(BaseModel):
    success: bool
    message: str
