from pydantic import BaseModel
from typing import Optional, List

class DataSourceBase(BaseModel):
    name: str
    type: str
    host: str
    port: int
    username: str
    database_name: str

class DataSourceCreate(DataSourceBase):
    password: str

class DataSourceUpdate(DataSourceBase):
    password: Optional[str] = None

class DataSource(DataSourceBase):
    id: int

    class Config:
        from_attributes = True

# Table structure schemas
class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: Optional[bool] = True
    default: Optional[str] = None

class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]
