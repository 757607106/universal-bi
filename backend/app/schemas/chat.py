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
