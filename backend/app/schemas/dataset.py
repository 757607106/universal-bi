from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class DatasetBase(BaseModel):
    name: str

class DatasetCreate(DatasetBase):
    datasource_id: int

class DatasetUpdateTables(BaseModel):
    schema_config: List[str]

class DatasetResponse(DatasetBase):
    id: int
    datasource_id: Optional[int] = None
    collection_name: Optional[str] = None
    schema_config: Optional[List[str]] = None
    training_status: str
    last_trained_at: Optional[datetime] = None

    class Config:
        from_attributes = True
