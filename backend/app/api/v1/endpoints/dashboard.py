from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import logging

from app.db.session import get_db
from app.models.metadata import Dashboard, DashboardCard, Dataset
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
    db: Session = Depends(get_db)
):
    """
    创建空看板
    """
    dashboard = Dashboard(
        name=dashboard_in.name,
        description=dashboard_in.description
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.get("/", response_model=List[DashboardResponse])
def list_dashboards(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取看板列表
    """
    dashboards = db.query(Dashboard).offset(skip).limit(limit).all()
    return dashboards


@router.get("/{id}", response_model=DashboardResponse)
def get_dashboard(
    id: int,
    db: Session = Depends(get_db)
):
    """
    获取看板详情（包含所有卡片）
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.post("/{id}/cards", response_model=DashboardCardResponse)
def add_card(
    id: int,
    card_in: DashboardCardCreate,
    db: Session = Depends(get_db)
):
    """
    添加卡片到看板
    """
    # 验证 Dashboard 存在
    dashboard = db.query(Dashboard).filter(Dashboard.id == id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # 验证 Dataset 存在
    dataset = db.query(Dataset).filter(Dataset.id == card_in.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
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
    db: Session = Depends(get_db)
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
        logger.error(f"SQL Execution failed for card {id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"SQL Execution Error: {str(e)}"
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
    db: Session = Depends(get_db)
):
    """
    删除卡片
    """
    card = db.query(DashboardCard).filter(DashboardCard.id == id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    dashboard_id = card.dashboard_id
    db.delete(card)
    
    # 更新 Dashboard 的 updated_at
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if dashboard:
        dashboard.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Card deleted successfully"}


@router.delete("/{id}")
def delete_dashboard(
    id: int,
    db: Session = Depends(get_db)
):
    """
    删除看板（级联删除所有卡片）
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    db.delete(dashboard)
    db.commit()
    return {"message": "Dashboard deleted successfully"}
