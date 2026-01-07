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


# Business Term Schemas
class BusinessTermBase(BaseModel):
    term: str
    definition: str

class BusinessTermCreate(BusinessTermBase):
    pass

class BusinessTermResponse(BusinessTermBase):
    id: int
    dataset_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Modeling Schemas
class AnalyzeRelationshipsRequest(BaseModel):
    datasource_id: int
    table_names: List[str]

class EdgeResponse(BaseModel):
    source: str
    target: str
    source_col: str
    target_col: str
    type: str
    confidence: Optional[str] = None

class FieldResponse(BaseModel):
    name: str
    type: str
    nullable: bool = True

class NodeResponse(BaseModel):
    table_name: str
    fields: List[FieldResponse]

class AnalyzeRelationshipsResponse(BaseModel):
    edges: List[EdgeResponse]
    nodes: List[NodeResponse]

class CreateViewRequest(BaseModel):
    datasource_id: int
    view_name: str
    sql: str
