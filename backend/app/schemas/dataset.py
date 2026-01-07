from pydantic import BaseModel
from typing import List, Optional, Any, Dict
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
    status: str = "pending"  # pending, training, completed, failed, paused
    modeling_config: Optional[Dict] = None  # 存储前端可视化建模的画布数据(nodes/edges)
    process_rate: int = 0  # 训练进度百分比 0-100
    error_msg: Optional[str] = None
    last_train_at: Optional[datetime] = None

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


# Training Log Schemas
class TrainingLogResponse(BaseModel):
    id: int
    dataset_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetUpdateStatus(BaseModel):
    """Update dataset training status"""
    status: Optional[str] = None  # pending, training, completed, failed, paused
    process_rate: Optional[int] = None
    error_msg: Optional[str] = None


class DatasetUpdateModelingConfig(BaseModel):
    """Update dataset modeling config"""
    modeling_config: Dict
