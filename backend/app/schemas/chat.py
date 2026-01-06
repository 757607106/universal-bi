from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    dataset_id: int
    question: str

class ChatResponse(BaseModel):
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    chart_type: str
    summary: Optional[str] = None
