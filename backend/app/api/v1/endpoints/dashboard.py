from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import logging

from app.db.session import get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dashboard, DashboardCard, Dataset, User
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardResponse,
    DashboardCardCreate,
    DashboardCardResponse,
    DashboardCardDataResponse
)
from app.services.db_inspector import DBInspector

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=DashboardResponse)
def create_dashboard(
    dashboard_in: DashboardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建空看板
    应用数据隔离：自动设置 owner_id
    """
    dashboard = Dashboard(
        name=dashboard_in.name,
        description=dashboard_in.description,
        owner_id=current_user.id  # 自动设置为当前用户
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.get("/", response_model=List[DashboardResponse])
def list_dashboards(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取看板列表
    应用数据隔离：普通用户只能查看自己的看板和公共资源
    """
    query = db.query(Dashboard)
    query = apply_ownership_filter(query, Dashboard, current_user)
    dashboards = query.offset(skip).limit(limit).all()
    return dashboards


@router.get("/{id}", response_model=DashboardResponse)
def get_dashboard(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取看板详情（包含所有卡片）
    应用数据隔离：只能查看自己的或公共的看板
    """
    query = db.query(Dashboard).filter(Dashboard.id == id)
    query = apply_ownership_filter(query, Dashboard, current_user)
    dashboard = query.first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
    return dashboard


@router.post("/{id}/cards", response_model=DashboardCardResponse)
def add_card(
    id: int,
    card_in: DashboardCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加卡片到看板
    应用数据隔离：需要验证 Dashboard 和 Dataset 的所有权
    """
    # 验证 Dashboard 存在且有权限
    dash_query = db.query(Dashboard).filter(Dashboard.id == id)
    dash_query = apply_ownership_filter(dash_query, Dashboard, current_user)
    dashboard = dash_query.first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以修改
    if dashboard.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")
    
    # 验证 Dataset 存在且有权限
    ds_query = db.query(Dataset).filter(Dataset.id == card_in.dataset_id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 创建卡片
    card = DashboardCard(
        dashboard_id=id,
        title=card_in.title,
        dataset_id=card_in.dataset_id,
        sql=card_in.sql,
        chart_type=card_in.chart_type,
        layout=card_in.layout
    )
    db.add(card)
    
    # 更新 Dashboard 的 updated_at
    dashboard.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(card)
    return card


@router.get("/cards/{id}/data", response_model=DashboardCardDataResponse)
def get_card_data(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刷新卡片数据 - 执行 SQL 并返回结果
    """
    # 获取卡片
    card = db.query(DashboardCard).filter(DashboardCard.id == id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # 获取关联的数据集
    dataset = db.query(Dataset).filter(Dataset.id == card.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 获取数据源
    datasource = dataset.datasource
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 执行 SQL
    try:
        engine = DBInspector.get_engine(datasource)
        df = pd.read_sql(card.sql, engine)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SQL Execution failed for card {id}: {error_msg}")
        
        # 区分错误类型：SQL 语法错误 vs 数据库连接错误
        if "Lost connection" in error_msg or "Connection reset" in error_msg:
            # 数据库连接问题，500 错误
            raise HTTPException(
                status_code=500,
                detail=f"数据库连接失败，请稍后重试"
            )
        else:
            # SQL 语法错误或其他业务错误，400 错误
            raise HTTPException(
                status_code=400,
                detail=f"SQL 执行错误: {error_msg}"
            )
    
    # 数据序列化
    def serialize(obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    rows = df.to_dict(orient='records')
    cleaned_rows = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            new_row[k] = serialize(v)
        cleaned_rows.append(new_row)
    
    return {
        "columns": df.columns.tolist(),
        "rows": cleaned_rows
    }


@router.delete("/cards/{id}")
def delete_card(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除卡片
    应用数据隔离：需要验证 Dashboard 的所有权
    """
    card = db.query(DashboardCard).filter(DashboardCard.id == id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    dashboard_id = card.dashboard_id
    
    # 验证 Dashboard 的所有权
    dash_query = db.query(Dashboard).filter(Dashboard.id == dashboard_id)
    dash_query = apply_ownership_filter(dash_query, Dashboard, current_user)
    dashboard = dash_query.first()
    
    if not dashboard:
        raise HTTPException(status_code=403, detail="Access denied to parent dashboard")
    
    # 额外检查：公共资源只有超级管理员可以修改
    if dashboard.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")
    
    db.delete(card)
    
    # 更新 Dashboard 的 updated_at
    dashboard.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Card deleted successfully"}


@router.delete("/{id}")
def delete_dashboard(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除看板（级联删除所有卡片）
    应用数据隔离：只能删除自己的看板
    """
    query = db.query(Dashboard).filter(Dashboard.id == id)
    query = apply_ownership_filter(query, Dashboard, current_user)
    dashboard = query.first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if dashboard.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    db.delete(dashboard)
    db.commit()
    return {"message": "Dashboard deleted successfully"}
