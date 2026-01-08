from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import logging

from app.db.session import get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dashboard, DashboardCard, Dataset, User, DashboardTemplate
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardResponse,
    DashboardCardCreate,
    DashboardCardResponse,
    DashboardCardDataResponse,
    DashboardTemplateCreate,
    DashboardTemplateUpdate,
    DashboardTemplateResponse,
    DashboardTemplateListResponse
)
from app.services.db_inspector import DBInspector
from sqlalchemy import or_

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


# ============ 看板模板相关 API ============

@router.post("/{id}/save-as-template", response_model=DashboardTemplateResponse)
def save_dashboard_as_template(
    id: int,
    template_in: DashboardTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    将看板保存为模板
    """
    # 验证 Dashboard 存在且有权限
    dash_query = db.query(Dashboard).filter(Dashboard.id == id)
    dash_query = apply_ownership_filter(dash_query, Dashboard, current_user)
    dashboard = dash_query.first()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found or access denied")

    # 构建模板配置（卡片快照）
    config = {
        "cards": []
    }
    for card in dashboard.cards:
        config["cards"].append({
            "title": card.title,
            "dataset_id": card.dataset_id,
            "sql": card.sql,
            "chart_type": card.chart_type,
            "layout": card.layout
        })

    # 创建模板
    template = DashboardTemplate(
        name=template_in.name,
        description=template_in.description,
        source_dashboard_id=id,
        config=config,
        owner_id=current_user.id,
        is_public=template_in.is_public
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(f"Dashboard {id} saved as template {template.id} by user {current_user.id}")
    return template


@router.get("/templates/", response_model=List[DashboardTemplateListResponse])
def list_templates(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取模板列表（包含公开模板和自己的私有模板）
    """
    templates = db.query(DashboardTemplate).filter(
        or_(
            DashboardTemplate.is_public == True,
            DashboardTemplate.owner_id == current_user.id
        )
    ).order_by(
        DashboardTemplate.created_at.desc()
    ).offset(skip).limit(limit).all()

    return templates


@router.get("/templates/{template_id}", response_model=DashboardTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取模板详情
    """
    template = db.query(DashboardTemplate).filter(
        DashboardTemplate.id == template_id,
        or_(
            DashboardTemplate.is_public == True,
            DashboardTemplate.owner_id == current_user.id
        )
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    return template


@router.post("/templates/{template_id}/create-dashboard", response_model=DashboardResponse)
def create_dashboard_from_template(
    template_id: int,
    name: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从模板创建新看板
    """
    # 获取模板
    template = db.query(DashboardTemplate).filter(
        DashboardTemplate.id == template_id,
        or_(
            DashboardTemplate.is_public == True,
            DashboardTemplate.owner_id == current_user.id
        )
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    # 创建新看板
    dashboard_name = name if name else f"{template.name} (副本)"
    dashboard = Dashboard(
        name=dashboard_name,
        description=template.description,
        owner_id=current_user.id
    )
    db.add(dashboard)
    db.flush()  # 获取 dashboard.id

    # 从模板配置创建卡片
    for card_config in template.config.get("cards", []):
        # 验证用户是否有权访问对应的 Dataset
        ds_query = db.query(Dataset).filter(Dataset.id == card_config["dataset_id"])
        ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
        dataset = ds_query.first()

        if not dataset:
            # 跳过无权访问的数据集的卡片
            logger.warning(f"Skipping card with dataset_id {card_config['dataset_id']} - user has no access")
            continue

        card = DashboardCard(
            dashboard_id=dashboard.id,
            title=card_config["title"],
            dataset_id=card_config["dataset_id"],
            sql=card_config["sql"],
            chart_type=card_config["chart_type"],
            layout=card_config.get("layout")
        )
        db.add(card)

    db.commit()
    db.refresh(dashboard)

    logger.info(f"Dashboard created from template {template_id} by user {current_user.id}")
    return dashboard


@router.patch("/templates/{template_id}", response_model=DashboardTemplateResponse)
def update_template(
    template_id: int,
    template_in: DashboardTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新模板（只能更新自己的模板）
    """
    template = db.query(DashboardTemplate).filter(
        DashboardTemplate.id == template_id,
        DashboardTemplate.owner_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    if template_in.name is not None:
        template.name = template_in.name
    if template_in.description is not None:
        template.description = template_in.description
    if template_in.is_public is not None:
        template.is_public = template_in.is_public

    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    return template


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除模板（只能删除自己的模板）
    """
    template = db.query(DashboardTemplate).filter(
        DashboardTemplate.id == template_id,
        DashboardTemplate.owner_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}
