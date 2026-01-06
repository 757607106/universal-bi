from pydantic import BaseModel
from typing import Optional

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
