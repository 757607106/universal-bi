from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dataset, DataSource, BusinessTerm, User
from app.schemas.dataset import (
    DatasetCreate, DatasetResponse, DatasetUpdateTables,
    BusinessTermCreate, BusinessTermResponse
)
from app.services.vanna_manager import VannaManager

router = APIRouter()

def run_training_task(dataset_id: int, table_names: list[str]):
    """
    Background task wrapper to ensure a separate DB session.
    """
    db = SessionLocal()
    try:
        VannaManager.train_dataset(dataset_id, table_names, db)
    finally:
        db.close()

@router.post("/", response_model=DatasetResponse)
def create_dataset(
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new dataset.
    应用数据隔离：需要验证 DataSource 的所有权
    """
    # 验证 DataSource 访问权限
    ds_query = db.query(DataSource).filter(DataSource.id == dataset_in.datasource_id)
    ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
    datasource = ds_query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")

    dataset = Dataset(
        name=dataset_in.name,
        datasource_id=dataset_in.datasource_id,
        training_status="pending",
        owner_id=current_user.id  # 自动设置为当前用户
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Auto-generate collection_name based on ID
    dataset.collection_name = f"vec_ds_{dataset.id}"
    db.commit()
    db.refresh(dataset)
    
    return dataset

@router.get("/", response_model=List[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List datasets.
    应用数据隔离：普通用户只能查看自己的数据集和公共资源
    """
    query = db.query(Dataset)
    query = apply_ownership_filter(query, Dataset, current_user)
    datasets = query.offset(skip).limit(limit).all()
    return datasets

@router.put("/{id}/tables", response_model=DatasetResponse)
def update_tables(
    id: int,
    config_in: DatasetUpdateTables,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update selected tables (schema_config) for a dataset.
    应用数据隔离：只能修改自己的数据集
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以修改
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")
        
    dataset.schema_config = config_in.schema_config
    db.commit()
    db.refresh(dataset)
    return dataset

@router.post("/{id}/train")
def train_dataset(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger training for a dataset.
    应用数据隔离：只能训练自己的数据集
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以训练
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot train public resources")
        
    if not dataset.schema_config:
        raise HTTPException(status_code=400, detail="No tables selected for training")
        
    # Check if already training? 
    if dataset.training_status == "training":
        # Optional: Allow restart or block? User didn't specify.
        # We'll allow it but maybe warn? For now just proceed.
        pass

    dataset.training_status = "pending" # Set to pending before background task picks it up (or directly training)
    # Actually VannaManager sets it to 'training'.
    # But to give immediate feedback, maybe we can set it here?
    # VannaManager logic:
    # dataset.training_status = "training"
    # So we don't strictly need to set it here, but it's good UI feedback if we set it to 'pending' or 'queued'.
    # The model default is 'pending'.
    
    background_tasks.add_task(run_training_task, id, dataset.schema_config)
    
    return {"message": "训练已开始"}


# Business Term Management Endpoints
@router.post("/{id}/terms", response_model=BusinessTermResponse)
def add_business_term(
    id: int,
    term_in: BusinessTermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a business term to a dataset and train it in Vanna.
    应用数据隔离：需要验证 Dataset 的所有权
    """
    # Verify dataset exists and user has access
    ds_query = db.query(Dataset).filter(Dataset.id == id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以添加术语
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot add terms to public resources")
    
    # Create business term in database
    business_term = BusinessTerm(
        dataset_id=id,
        term=term_in.term,
        definition=term_in.definition,
        owner_id=current_user.id  # 自动设置为当前用户
    )
    db.add(business_term)
    db.commit()
    db.refresh(business_term)
    
    # Train the term in Vanna
    try:
        VannaManager.train_term(
            dataset_id=id,
            term=term_in.term,
            definition=term_in.definition,
            db_session=db
        )
    except Exception as e:
        # Rollback database if Vanna training fails
        db.delete(business_term)
        db.commit()
        raise HTTPException(status_code=500, detail=f"训练术语失败: {str(e)}")
    
    return business_term


@router.get("/{id}/terms", response_model=List[BusinessTermResponse])
def list_business_terms(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all business terms for a dataset.
    应用数据隔离：需要验证 Dataset 的访问权
    """
    # Verify dataset access
    ds_query = db.query(Dataset).filter(Dataset.id == id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 查询术语（也应用隔离）
    term_query = db.query(BusinessTerm).filter(BusinessTerm.dataset_id == id)
    term_query = apply_ownership_filter(term_query, BusinessTerm, current_user)
    terms = term_query.all()
    
    return terms


@router.delete("/terms/{term_id}")
def delete_business_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a business term from database.
    Note: Vanna Legacy API does not provide a direct way to remove specific training data,
    so this only removes from database. The term will remain in the vector store.
    应用数据隔离：只能删除自己的术语
    """
    term_query = db.query(BusinessTerm).filter(BusinessTerm.id == term_id)
    term_query = apply_ownership_filter(term_query, BusinessTerm, current_user)
    term = term_query.first()
    
    if not term:
        raise HTTPException(status_code=404, detail="Business term not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if term.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    db.delete(term)
    db.commit()
    
    return {"message": "术语已删除（注：向量库中的训练数据仍保留）"}
