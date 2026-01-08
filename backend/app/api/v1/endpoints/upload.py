"""
文件上传API端点 - 处理Excel/CSV文件上传和自动分析
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.metadata import User, Dataset, DataSource
from app.schemas.upload import FileUploadResponse, UploadedDatasetInfo
from app.services.file_etl import FileETLService
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

