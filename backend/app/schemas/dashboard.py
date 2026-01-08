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


# ============ 看板模板相关 Schema ============

class DashboardTemplateCreate(BaseModel):
    """创建模板请求"""
    name: str
    description: Optional[str] = None
    is_public: bool = False


class DashboardTemplateUpdate(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class DashboardTemplateResponse(BaseModel):
    """模板响应"""
    id: int
    name: str
    description: Optional[str]
    source_dashboard_id: Optional[int]
    config: Dict[str, Any]
    owner_id: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardTemplateListResponse(BaseModel):
    """模板列表响应（不含config详情）"""
    id: int
    name: str
    description: Optional[str]
    is_public: bool
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
