"""
数据表管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import User, Dataset
from app.models.data_table import Folder, DataTable, TableField
from app.schemas.data_table import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    DataTableCreate,
    DataTableUpdate,
    DataTableResponse,
    DataTableWithFields,
    ExcelPreviewResponse,
    UpdateFieldsRequest,
    DataQueryRequest,
    DataQueryResponse
)
from app.schemas.dataset import DatasetResponse
from app.services.file_etl import FileETLService
from app.services.data_table_service import DataTableService
from app.services.vanna import VannaTrainingService
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _train_data_table_dataset(dataset_id: int, table_name: str):
    """后台训练任务"""
    db = SessionLocal()
    try:
        VannaTrainingService.train_dataset(dataset_id, [table_name], db)
    finally:
        db.close()


# ============ 文件夹管理 API ============

@router.post("/folders", response_model=FolderResponse)
def create_folder(
    folder_in: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """新建文件夹"""
    try:
        # 如果指定了父文件夹，检查是否存在且属于当前用户
        if folder_in.parent_id:
            parent = db.query(Folder).filter(
                Folder.id == folder_in.parent_id,
                Folder.owner_id == current_user.id
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="父文件夹不存在")
        
        # 创建文件夹
        folder = Folder(
            name=folder_in.name,
            parent_id=folder_in.parent_id,
            owner_id=current_user.id
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)
        
        logger.info("Folder created", folder_id=folder.id, user_id=current_user.id)
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create folder", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")


@router.get("/folders", response_model=List[FolderResponse])
def get_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文件夹列表"""
    try:
        folders = db.query(Folder).filter(
            Folder.owner_id == current_user.id
        ).order_by(Folder.created_at.desc()).all()
        
        return folders
        
    except Exception as e:
        logger.error("Failed to get folders", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文件夹列表失败: {str(e)}")


@router.put("/folders/{id}", response_model=FolderResponse)
def update_folder(
    id: int,
    folder_in: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重命名文件夹"""
    try:
        folder = db.query(Folder).filter(
            Folder.id == id,
            Folder.owner_id == current_user.id
        ).first()
        
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        if folder_in.name is not None:
            folder.name = folder_in.name
        if folder_in.parent_id is not None:
            folder.parent_id = folder_in.parent_id
        
        db.commit()
        db.refresh(folder)
        
        logger.info("Folder updated", folder_id=id, user_id=current_user.id)
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update folder", folder_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新文件夹失败: {str(e)}")


@router.delete("/folders/{id}")
def delete_folder(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除文件夹"""
    try:
        folder = db.query(Folder).filter(
            Folder.id == id,
            Folder.owner_id == current_user.id
        ).first()
        
        if not folder:
            raise HTTPException(status_code=404, detail="文件夹不存在")
        
        # 检查是否有子文件夹或数据表
        has_children = db.query(Folder).filter(Folder.parent_id == id).count() > 0
        has_tables = db.query(DataTable).filter(DataTable.folder_id == id).count() > 0
        
        if has_children or has_tables:
            raise HTTPException(status_code=400, detail="文件夹不为空，无法删除")
        
        db.delete(folder)
        db.commit()
        
        logger.info("Folder deleted", folder_id=id, user_id=current_user.id)
        return {"success": True, "message": "文件夹已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete folder", folder_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除文件夹失败: {str(e)}")


# ============ 数据表管理 API ============

@router.post("/preview-excel", response_model=ExcelPreviewResponse)
async def preview_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """预览Excel文件"""
    try:
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 验证文件
        FileETLService.validate_file(file.filename, file_size)
        
        # 预览文件
        preview_data = FileETLService.preview_excel(file_content, file.filename)
        
        logger.info("Excel previewed", filename=file.filename, user_id=current_user.id)
        return preview_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to preview excel", filename=file.filename, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览Excel失败: {str(e)}")


@router.post("/", response_model=DataTableResponse)
async def create_data_table(
    display_name: str = Form(...),
    creation_method: str = Form(...),
    datasource_id: Optional[int] = Form(None),
    folder_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    source_table_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建数据表
    注意：由于需要处理文件上传，这个端点需要特殊处理
    实际使用时建议分为两个端点：一个处理Excel上传，一个处理数据源表选择
    """
    try:
        # 这里简化处理，实际应该根据creation_method分别处理
        if creation_method == 'excel_upload':
            if not file:
                raise HTTPException(status_code=400, detail="缺少文件")
            
            # 自动创建/获取上传数据源（如果未提供datasource_id）
            if not datasource_id:
                upload_ds = FileETLService.create_upload_datasource(
                    db=db,
                    user=current_user,
                    datasource_name="本地上传数据源"
                )
                datasource_id = upload_ds.id
                logger.info(
                    "Auto-created upload datasource",
                    datasource_id=datasource_id,
                    user_id=current_user.id
                )
            
            # 读取文件
            file_content = await file.read()
            
            # 解析并预览（获取字段配置）
            _, fields_info = FileETLService.parse_file_with_types(file_content, file.filename)
            
            # 创建字段配置对象
            from app.schemas.data_table import TableFieldConfig
            fields_config = [TableFieldConfig(**field) for field in fields_info]
            
            # 创建数据表
            data_table = DataTableService.create_data_table_from_excel(
                display_name=display_name,
                file_content=file_content,
                filename=file.filename,
                fields_config=fields_config,
                datasource_id=datasource_id,
                folder_id=folder_id,
                description=description,
                user=current_user,
                db_session=db
            )
            
        elif creation_method == 'datasource_table':
            if not datasource_id:
                raise HTTPException(status_code=400, detail="缺少数据源ID")
            if not source_table_name:
                raise HTTPException(status_code=400, detail="缺少源表名")
            
            # 需要先获取表结构（这里简化，实际应该先调用预览API）
            raise HTTPException(status_code=501, detail="此功能需要先调用预览API获取字段配置")
            
        else:
            raise HTTPException(status_code=400, detail="不支持的创建方式")
        
        return data_table
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create data table", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建数据表失败: {str(e)}")


@router.get("/", response_model=List[DataTableResponse])
def get_data_tables(
    folder_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据表列表"""
    try:
        query = db.query(DataTable).filter(
            DataTable.owner_id == current_user.id
        )
        
        if folder_id is not None:
            query = query.filter(DataTable.folder_id == folder_id)
        
        tables = query.order_by(DataTable.created_at.desc()).all()
        
        return tables
        
    except Exception as e:
        logger.error("Failed to get data tables", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据表列表失败: {str(e)}")


@router.get("/{id}", response_model=DataTableWithFields)
def get_data_table(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查看数据表详情"""
    try:
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        return data_table
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get data table", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据表详情失败: {str(e)}")


@router.put("/{id}", response_model=DataTableResponse)
def update_data_table(
    id: int,
    table_in: DataTableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """编辑数据表"""
    try:
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        if table_in.display_name is not None:
            data_table.display_name = table_in.display_name
        if table_in.folder_id is not None:
            data_table.folder_id = table_in.folder_id
        if table_in.description is not None:
            data_table.description = table_in.description
        if table_in.status is not None:
            data_table.status = table_in.status
        
        data_table.modifier_id = current_user.id
        
        db.commit()
        db.refresh(data_table)
        
        logger.info("Data table updated", table_id=id, user_id=current_user.id)
        return data_table
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update data table", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新数据表失败: {str(e)}")


@router.delete("/{id}")
def delete_data_table(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除数据表"""
    try:
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 调用服务删除数据表
        DataTableService.delete_data_table(
            data_table_id=id,
            user=current_user,
            db_session=db
        )
        
        return {"success": True, "message": "数据表已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete data table", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除数据表失败: {str(e)}")


@router.put("/{id}/fields", response_model=DataTableResponse)
def update_fields(
    id: int,
    request: UpdateFieldsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新字段配置"""
    try:
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 调用服务更新字段配置
        updated_table = DataTableService.update_field_config(
            data_table_id=id,
            fields_config=request.fields,
            user=current_user,
            db_session=db
        )
        
        return updated_table
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update fields", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新字段配置失败: {str(e)}")


@router.get("/{id}/data", response_model=DataQueryResponse)
def query_data(
    id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """查询表数据"""
    try:
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 调用服务查询数据
        result = DataTableService.query_data_table(
            data_table_id=id,
            page=page,
            page_size=page_size,
            db_session=db
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query data", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询数据失败: {str(e)}")


@router.get("/{id}/dataset", response_model=DatasetResponse)
def get_or_create_dataset(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为数据表获取或自动创建对应的Dataset，用于智能问答分析
    
    - 如果DataTable已关联Dataset，直接返回
    - 如果未关联，自动创建新的Dataset并后台训练
    """
    try:
        # 验证DataTable访问权限
        data_table = db.query(DataTable).filter(
            DataTable.id == id,
            DataTable.owner_id == current_user.id
        ).first()
        
        if not data_table:
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 查找是否已有关联的Dataset
        # Dataset的schema_config包含物理表名
        existing_dataset = db.query(Dataset).filter(
            Dataset.datasource_id == data_table.datasource_id,
            Dataset.owner_id == current_user.id
        ).all()
        
        # 查找包含该表的Dataset
        for ds in existing_dataset:
            if ds.schema_config and data_table.physical_table_name in ds.schema_config:
                logger.info(
                    "Found existing dataset for data table",
                    data_table_id=id,
                    dataset_id=ds.id
                )
                return ds
        
        # 没有找到，创建新的Dataset
        collection_name = f"vanna_{uuid.uuid4().hex[:16]}"
        new_dataset = Dataset(
            name=f"{data_table.display_name}",
            datasource_id=data_table.datasource_id,
            collection_name=collection_name,
            schema_config=[data_table.physical_table_name],
            status="pending",
            owner_id=current_user.id
        )
        
        db.add(new_dataset)
        db.commit()
        db.refresh(new_dataset)
        
        logger.info(
            "Created new dataset for data table",
            data_table_id=id,
            dataset_id=new_dataset.id,
            table_name=data_table.physical_table_name
        )
        
        # 后台触发训练
        background_tasks.add_task(
            _train_data_table_dataset,
            dataset_id=new_dataset.id,
            table_name=data_table.physical_table_name
        )
        
        return new_dataset
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get or create dataset", table_id=id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取或创建Dataset失败: {str(e)}")
