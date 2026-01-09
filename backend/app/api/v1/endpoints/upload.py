"""
文件上传API端点 - 处理Excel/CSV文件上传和自动分析
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List, Dict
import uuid
import re

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user
from app.models.metadata import User, Dataset, DataSource
from app.schemas.upload import FileUploadResponse, UploadedDatasetInfo, MultiFileUploadResponse
from app.services.file_etl import FileETLService
from app.services.duckdb_service import DuckDBService
from app.services.vanna import VannaTrainingService
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/excel", response_model=FileUploadResponse)
async def upload_excel_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传Excel/CSV文件并自动创建数据集
    
    工作流程：
    1. 验证文件格式和大小
    2. 解析文件内容为DataFrame
    3. 创建或获取上传数据源
    4. 将数据写入数据库（专用Schema）
    5. 创建Dataset记录
    6. 后台触发Vanna训练
    
    Args:
        file: 上传的文件
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        FileUploadResponse: 上传结果
    """
    logger.info(
        "File upload request received",
        user_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type
    )
    
    try:
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 1. 验证文件
        FileETLService.validate_file(file.filename, file_size)
        
        # 2. 解析文件
        df = FileETLService.parse_file(file_content, file.filename)
        row_count = len(df)
        column_count = len(df.columns)
        
        # 3. 创建或获取上传数据源
        datasource = FileETLService.create_upload_datasource(
            db=db,
            user=current_user,
            datasource_name=f"{current_user.username}_uploads"
        )
        
        # 4. 生成表名并写入数据库
        table_name = FileETLService.generate_table_name(
            user_id=current_user.id,
            filename=file.filename
        )
        
        FileETLService.write_to_database(
            df=df,
            table_name=table_name,
            datasource=datasource,
            db_session=db
        )
        
        # 5. 创建Dataset记录
        collection_name = f"vanna_{uuid.uuid4().hex[:16]}"
        dataset = Dataset(
            name=file.filename,
            datasource_id=datasource.id,
            collection_name=collection_name,
            schema_config=[table_name],  # 只包含上传的表
            status="pending",
            owner_id=current_user.id
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        logger.info(
            "Dataset created for uploaded file",
            dataset_id=dataset.id,
            table_name=table_name,
            user_id=current_user.id
        )
        
        # 6. 后台触发训练
        background_tasks.add_task(
            _train_uploaded_dataset,
            dataset_id=dataset.id,
            table_names=[table_name]
        )
        
        return FileUploadResponse(
            success=True,
            message=f"文件上传成功！已加载表格 [{file.filename}]，您可以直接提问了。",
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            datasource_id=datasource.id,
            table_name=table_name,
            row_count=row_count,
            column_count=column_count
        )
        
    except ValueError as e:
        logger.error(
            "File upload validation failed",
            user_id=current_user.id,
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "File upload failed",
            user_id=current_user.id,
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/datasets", response_model=List[UploadedDatasetInfo])
async def list_uploaded_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户上传的所有数据集
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        List[UploadedDatasetInfo]: 上传的数据集列表
    """
    # 查询用户的上传数据源
    upload_datasource = db.query(DataSource).filter(
        DataSource.owner_id == current_user.id,
        DataSource.type == "upload"
    ).first()
    
    if not upload_datasource:
        return []
    
    # 查询该数据源下的所有数据集
    datasets = db.query(Dataset).filter(
        Dataset.datasource_id == upload_datasource.id,
        Dataset.owner_id == current_user.id
    ).order_by(Dataset.id.desc()).all()
    
    result = []
    for ds in datasets:
        # 获取行数和列数（从schema_config获取表名，然后查询）
        table_name = ds.schema_config[0] if ds.schema_config else None
        row_count = 0
        column_count = 0
        
        if table_name:
            try:
                from sqlalchemy import create_engine, inspect
                from app.core.security import decrypt_password
                
                # 构建数据库连接
                password = decrypt_password(upload_datasource.password_encrypted)
                db_url = f"mysql+pymysql://{upload_datasource.username}:{password}@{upload_datasource.host}:{upload_datasource.port}/{upload_datasource.database_name}?charset=utf8mb4"
                engine = create_engine(db_url)
                
                # 获取表信息
                inspector = inspect(engine)
                if table_name in inspector.get_table_names():
                    columns = inspector.get_columns(table_name)
                    column_count = len(columns)
                    
                    # 查询行数
                    with engine.connect() as conn:
                        result_proxy = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = result_proxy.scalar()
            except Exception as e:
                logger.warning(
                    "Failed to get table info",
                    table_name=table_name,
                    error=str(e)
                )
        
        result.append(UploadedDatasetInfo(
            dataset_id=ds.id,
            dataset_name=ds.name,
            file_name=ds.name,
            row_count=row_count,
            column_count=column_count,
            created_at=ds.created_at.isoformat() if ds.created_at else "",
            status=ds.status,
            is_uploaded=True
        ))
    
    return result


def _train_uploaded_dataset(dataset_id: int, table_names: List[str]):
    """
    后台任务：训练上传的数据集
    
    Args:
        dataset_id: 数据集ID
        table_names: 表名列表
    """
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        logger.info(
            "Starting background training for uploaded dataset",
            dataset_id=dataset_id,
            tables=table_names
        )
        
        # 调用训练服务
        VannaTrainingService.train_dataset(
            dataset_id=dataset_id,
            table_names=table_names,
            db_session=db
        )
        
        logger.info(
            "Background training completed",
            dataset_id=dataset_id
        )
        
    except Exception as e:
        logger.error(
            "Background training failed",
            dataset_id=dataset_id,
            error=str(e),
            exc_info=True
        )
    finally:
        db.close()


def _sanitize_table_name(filename: str) -> str:
    """
    清理文件名以生成合法的表名
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的表名
    """
    # 移除扩展名
    name = filename.rsplit('.', 1)[0]
    
    # 替换特殊字符为下划线
    name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', name)
    
    # 移除多余的下划线
    name = re.sub(r'_+', '_', name)
    
    # 移除首尾下划线
    name = name.strip('_')
    
    # 如果以数字开头，添加前缀
    if name and name[0].isdigit():
        name = 'tbl_' + name
    
    # 限制长度
    if len(name) > 50:
        name = name[:50]
    
    return name.lower()


@router.post("/multi-files", response_model=MultiFileUploadResponse)
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    dataset_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量上传多个 Excel/CSV 文件并创建 Dataset
    
    工作流程：
    1. 验证所有文件（格式、大小）
    2. 解析为 DataFrame
    3. 创建 DuckDB 数据库
    4. 导入所有表
    5. 创建 Dataset 记录
    6. 后台触发 AI 关系推理和训练
    
    Args:
        files: 上传的文件列表
        dataset_name: 数据集名称
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        MultiFileUploadResponse: 上传结果
    """
    logger.info(
        "Multi-file upload request received",
        user_id=current_user.id,
        dataset_name=dataset_name,
        file_count=len(files)
    )
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="单次最多上传 10 个文件")
    
    try:
        # 1. 验证和解析所有文件
        dataframes: Dict[str, 'pd.DataFrame'] = {}
        file_info = []
        
        for file in files:
            content = await file.read()
            file_size = len(content)
            
            # 验证文件
            FileETLService.validate_file(file.filename, file_size)
            
            # 解析文件
            df = FileETLService.parse_file(content, file.filename)
            
            # 生成表名
            table_name = _sanitize_table_name(file.filename)
            
            # 如果表名重复，添加后缀
            if table_name in dataframes:
                counter = 1
                while f"{table_name}_{counter}" in dataframes:
                    counter += 1
                table_name = f"{table_name}_{counter}"
            
            dataframes[table_name] = df
            file_info.append({
                "filename": file.filename,
                "table_name": table_name,
                "rows": len(df),
                "columns": len(df.columns)
            })
            
            logger.info(
                f"Parsed file: {file.filename} -> {table_name}",
                rows=len(df),
                columns=len(df.columns)
            )
        
        # 2. 创建 Dataset 记录
        dataset = Dataset(
            name=dataset_name,
            datasource_id=None,  # DuckDB 数据集不需要传统数据源
            status="pending",
            owner_id=current_user.id,
            schema_config=list(dataframes.keys())
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        # 生成 collection_name（必须在获取dataset.id之后）
        dataset.collection_name = f"vec_ds_{dataset.id}"
        
        # 3. 创建 DuckDB 数据库并导入数据
        db_path = DuckDBService.create_dataset_database(dataset.id)
        stats = DuckDBService.import_dataframes(db_path, dataframes)
        
        # 4. 更新 Dataset 元数据（包括 collection_name 和 duckdb_path）
        dataset.duckdb_path = db_path
        db.commit()  # 这里会同时保存 collection_name 和 duckdb_path
        db.refresh(dataset)
        
        logger.info(
            "Dataset created successfully",
            dataset_id=dataset.id,
            duckdb_path=db_path,
            tables=list(stats.keys())
        )
        
        # 5. 后台任务：训练 DDL（暂不做关系推理，在用户确认建模后再做）
        background_tasks.add_task(
            _train_uploaded_dataset,
            dataset_id=dataset.id,
            table_names=list(dataframes.keys())
        )
        
        # 计算总行数
        total_rows = sum(stats.values())
        
        return MultiFileUploadResponse(
            success=True,
            message=f"成功上传 {len(files)} 个文件，共 {total_rows} 行数据",
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            tables=stats,
            total_files=len(files),
            total_rows=total_rows,
            duckdb_path=db_path
        )
        
    except ValueError as e:
        logger.error(
            "Multi-file upload validation failed",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Multi-file upload failed",
            user_id=current_user.id,
            dataset_name=dataset_name,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

