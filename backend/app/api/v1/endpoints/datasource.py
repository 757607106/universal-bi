from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.session import SessionLocal, get_db
from app.models.metadata import DataSource
from app.schemas.datasource import DataSource as DataSourceSchema, DataSourceCreate
from app.services.db_inspector import DBInspector
from app.core.security import encrypt_password

router = APIRouter()

@router.post("/test", response_model=bool)
def test_datasource_connection(ds_in: DataSourceCreate):
    """
    Test connection to a data source without saving it.
    """
    ds_info = ds_in.dict()
    return DBInspector.test_connection(ds_info)

@router.post("/", response_model=DataSourceSchema)
def create_datasource(ds_in: DataSourceCreate, db: Session = Depends(get_db)):
    """
    Create new data source.
    """
    # Check if name exists? Optional but good practice.
    
    # Encrypt password
    encrypted_password = encrypt_password(ds_in.password)
    
    db_obj = DataSource(
        name=ds_in.name,
        type=ds_in.type,
        host=ds_in.host,
        port=ds_in.port,
        username=ds_in.username,
        password_encrypted=encrypted_password,
        database_name=ds_in.database_name
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[DataSourceSchema])
def read_datasources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve data sources.
    """
    datasources = db.query(DataSource).offset(skip).limit(limit).all()
    return datasources

@router.delete("/{id}", response_model=bool)
def delete_datasource(id: int, db: Session = Depends(get_db)):
    """
    Delete a data source.
    """
    datasource = db.query(DataSource).filter(DataSource.id == id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    db.delete(datasource)
    db.commit()
    return True

@router.get("/{id}/tables", response_model=List[str])
def get_datasource_tables(id: int, db: Session = Depends(get_db)):
    """
    Get all table names for a data source.
    """
    datasource = db.query(DataSource).filter(DataSource.id == id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    try:
        return DBInspector.get_table_names(datasource)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables: {str(e)}")

@router.get("/{id}/tables/{table_name}/preview", response_model=Dict[str, Any])
def preview_table_data(id: int, table_name: str, db: Session = Depends(get_db)):
    """
    Preview data for a specific table.
    """
    datasource = db.query(DataSource).filter(DataSource.id == id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    try:
        return DBInspector.get_table_data(datasource, table_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview data: {str(e)}")
