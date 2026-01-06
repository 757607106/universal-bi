from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# DashboardCard Schemas
class DashboardCardBase(BaseModel):
    title: str
    dataset_id: int
    sql: str
    chart_type: str
    layout: Optional[Dict[str, Any]] = None


class DashboardCardCreate(DashboardCardBase):
    pass


class DashboardCardResponse(DashboardCardBase):
    id: int
    dashboard_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardCardDataResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]


# Dashboard Schemas
class DashboardBase(BaseModel):
    name: str
    description: Optional[str] = None


class DashboardCreate(DashboardBase):
    pass


class DashboardResponse(DashboardBase):
    id: int
    created_at: datetime
    updated_at: datetime
    cards: List[DashboardCardResponse] = []
    
    class Config:
        from_attributes = True
