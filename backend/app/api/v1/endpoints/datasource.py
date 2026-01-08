from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.db.session import SessionLocal, get_db
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import DataSource, User
from app.schemas.datasource import (
    DataSource as DataSourceSchema,
    DataSourceCreate,
    DataSourceUpdate,
    TableInfo
)
from app.services.db_inspector import DBInspector
from app.core.security import encrypt_password, decrypt_password

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


@router.put("/{id}", response_model=DataSourceSchema)
def update_datasource(
    id: int,
    ds_in: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新数据源配置。
    如果提供了新密码，会重新加密存储。
    应用数据隔离：普通用户只能更新自己的资源
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()

    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")

    # 额外检查：公共资源只有超级管理员可以修改
    if datasource.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")

    # 更新基本信息
    datasource.name = ds_in.name
    datasource.type = ds_in.type
    datasource.host = ds_in.host
    datasource.port = ds_in.port
    datasource.username = ds_in.username
    datasource.database_name = ds_in.database_name

    # 如果提供了新密码，重新加密
    if ds_in.password:
        datasource.password_encrypted = encrypt_password(ds_in.password)

    db.commit()
    db.refresh(datasource)
    return datasource


@router.post("/{id}/test-connection")
def test_existing_datasource_connection(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试现有数据源的连接。
    用于检查数据源是否可以正常连接（密码是否正确、网络是否通等）。
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()

    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")

    # 检查密码是否可以解密
    password = ""
    password_error = None
    if datasource.password_encrypted:
        try:
            password = decrypt_password(datasource.password_encrypted)
        except Exception as e:
            password_error = f"密码解密失败: {str(e)}"
            logger.error(f"Failed to decrypt password for datasource {id}: {e}")

    if password_error:
        return {
            "success": False,
            "error": password_error,
            "error_type": "password_decrypt_failed",
            "message": "数据源密码无法解密，请重新设置密码"
        }

    # 构建连接信息并测试
    ds_info = {
        "type": datasource.type,
        "host": datasource.host,
        "port": datasource.port,
        "username": datasource.username,
        "password": password,
        "database_name": datasource.database_name
    }

    try:
        success = DBInspector.test_connection(ds_info)
        if success:
            return {
                "success": True,
                "message": "连接成功"
            }
        else:
            return {
                "success": False,
                "error": "连接失败",
                "error_type": "connection_failed",
                "message": "无法连接到数据库，请检查配置"
            }
    except Exception as e:
        error_msg = str(e)
        error_type = "connection_error"

        # 分析错误类型
        if "Access denied" in error_msg:
            error_type = "access_denied"
            message = "访问被拒绝，请检查用户名和密码"
        elif "Connection refused" in error_msg or "connect" in error_msg.lower():
            error_type = "connection_refused"
            message = "连接被拒绝，请检查主机地址和端口"
        elif "Unknown database" in error_msg:
            error_type = "unknown_database"
            message = "数据库不存在，请检查数据库名称"
        else:
            message = f"连接失败: {error_msg}"

        return {
            "success": False,
            "error": error_msg,
            "error_type": error_type,
            "message": message
        }


@router.post("/{id}/reconnect", response_model=DataSourceSchema)
def reconnect_datasource(
    id: int,
    password: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重新连接数据源（更新密码并测试连接）。
    用于密码过期或密码解密失败时重新设置密码。
    """
    query = db.query(DataSource).filter(DataSource.id == id)
    query = apply_ownership_filter(query, DataSource, current_user)
    datasource = query.first()

    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")

    # 额外检查：公共资源只有超级管理员可以修改
    if datasource.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")

    # 先测试新密码是否能连接
    ds_info = {
        "type": datasource.type,
        "host": datasource.host,
        "port": datasource.port,
        "username": datasource.username,
        "password": password,
        "database_name": datasource.database_name
    }

    try:
        success = DBInspector.test_connection(ds_info)
        if not success:
            raise HTTPException(status_code=400, detail="连接测试失败，请检查密码是否正确")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接测试失败: {str(e)}")

    # 连接成功，更新密码
    datasource.password_encrypted = encrypt_password(password)
    db.commit()
    db.refresh(datasource)

    return datasource

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

    # 先检查密码是否可以解密
    password = ""
    if datasource.password_encrypted:
        try:
            password = decrypt_password(datasource.password_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt password for datasource {id}: {e}")
            raise HTTPException(
                status_code=400,
                detail="数据源密码无法解密，请使用「重新连接」功能重新设置密码"
            )

    if not password:
        raise HTTPException(
            status_code=400,
            detail="数据源未配置密码，请使用「重新连接」功能设置密码"
        )

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
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to fetch tables: {e}")

        # 分析错误类型并给出更友好的提示
        if "Access denied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="数据库访问被拒绝，请检查用户名和密码是否正确，或使用「重新连接」功能重新设置密码"
            )
        elif "Connection refused" in error_msg or "connect" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="无法连接到数据库，请检查主机地址和端口是否正确"
            )
        elif "Unknown database" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="数据库不存在，请检查数据库名称是否正确"
            )
        else:
            raise HTTPException(status_code=500, detail=f"获取表列表失败: {error_msg}")

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
