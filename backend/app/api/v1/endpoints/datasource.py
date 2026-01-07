from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.db.session import SessionLocal, get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import DataSource, User
from app.schemas.datasource import (
    DataSource as DataSourceSchema, 
    DataSourceCreate,
    TableInfo
)
from app.services.db_inspector import DBInspector
from app.core.security import encrypt_password

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/test", response_model=bool)
def test_datasource_connection(
    ds_in: DataSourceCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Test connection to a data source without saving it.
    """
    ds_info = ds_in.dict()
    return DBInspector.test_connection(ds_info)

@router.post("/", response_model=DataSourceSchema)
def create_datasource(
    ds_in: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        database_name=ds_in.database_name,
        owner_id=current_user.id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[DataSourceSchema])
def read_datasources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve data sources.
    应用数据隔离：普通用户只能查看自己的数据源和公共资源
    """
    query = db.query(DataSource)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasources = query.offset(skip).limit(limit).all()
    return datasources

@router.delete("/{id}", response_model=bool)
def delete_datasource(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a data source.
    应用数据隔离：普通用户只能删除自己的资源，超级管理员可以删除任何资源
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if datasource.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    db.delete(datasource)
    db.commit()
    return True

@router.get("/{id}/tables", response_model=List[TableInfo])
def get_datasource_tables(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all table names and structures for a data source.
    应用数据隔离：只能查看自己的或公共的数据源
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")
    
    try:
        from sqlalchemy import inspect as sa_inspect
        
        # Get table names
        table_names = DBInspector.get_table_names(datasource)
        
        # Get engine and inspector
        engine = DBInspector.get_engine(datasource)
        inspector = sa_inspect(engine)
        
        # Build table info with columns
        tables_info = []
        for table_name in table_names:
            try:
                columns = inspector.get_columns(table_name)
                column_info = [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col.get('nullable', True),
                        'default': str(col.get('default')) if col.get('default') is not None else None
                    }
                    for col in columns
                ]
                
                tables_info.append({
                    'name': table_name,
                    'columns': column_info
                })
            except Exception as e:
                logger.warning(f"Failed to get columns for table {table_name}: {e}")
                # Include table even if column fetch fails
                tables_info.append({
                    'name': table_name,
                    'columns': []
                })
        
        return tables_info
    except Exception as e:
        logger.error(f"Failed to fetch tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables: {str(e)}")

@router.get("/{id}/tables/{table_name}/preview", response_model=Dict[str, Any])
def preview_table_data(
    id: int,
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview data for a specific table.
    应用数据隔离：只能查看自己的或公共的数据源
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")
    
    try:
        return DBInspector.get_table_data(datasource, table_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview data: {str(e)}")
