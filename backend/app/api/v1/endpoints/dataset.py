from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db, SessionLocal
from app.models.metadata import Dataset, DataSource, BusinessTerm
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
    db: Session = Depends(get_db)
):
    """
    Create a new dataset.
    """
    datasource = db.query(DataSource).filter(DataSource.id == dataset_in.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")

    dataset = Dataset(
        name=dataset_in.name,
        datasource_id=dataset_in.datasource_id,
        training_status="pending"
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
    db: Session = Depends(get_db)
):
    """
    List datasets.
    """
    datasets = db.query(Dataset).offset(skip).limit(limit).all()
    return datasets

@router.put("/{id}/tables", response_model=DatasetResponse)
def update_tables(
    id: int,
    config_in: DatasetUpdateTables,
    db: Session = Depends(get_db)
):
    """
    Update selected tables (schema_config) for a dataset.
    """
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    dataset.schema_config = config_in.schema_config
    db.commit()
    db.refresh(dataset)
    return dataset

@router.post("/{id}/train")
def train_dataset(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger training for a dataset.
    """
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
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
    db: Session = Depends(get_db)
):
    """
    Add a business term to a dataset and train it in Vanna.
    """
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create business term in database
    business_term = BusinessTerm(
        dataset_id=id,
        term=term_in.term,
        definition=term_in.definition
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
    db: Session = Depends(get_db)
):
    """
    Get all business terms for a dataset.
    """
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    terms = db.query(BusinessTerm).filter(BusinessTerm.dataset_id == id).all()
    return terms


@router.delete("/terms/{term_id}")
def delete_business_term(
    term_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a business term from database.
    Note: Vanna Legacy API does not provide a direct way to remove specific training data,
    so this only removes from database. The term will remain in the vector store.
    """
    term = db.query(BusinessTerm).filter(BusinessTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Business term not found")
    
    db.delete(term)
    db.commit()
    
    return {"message": "术语已删除（注：向量库中的训练数据仍保留）"}
