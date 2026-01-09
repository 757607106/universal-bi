from pydantic import BaseModel
from typing import Optional, List

class DataSourceBase(BaseModel):
    name: str
    type: str
    host: str
    port: int
    username: str
    database_name: str

class DataSourceTestConnection(BaseModel):
    """用于测试数据库连接的 Schema (name 可选)"""
    name: Optional[str] = None  # 测试连接时 name 可以为空
    type: str
    host: str
    port: int
    username: str
    password: str
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
