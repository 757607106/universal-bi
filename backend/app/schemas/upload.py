"""
Excel/CSV文件上传相关的Schema定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class FileUploadResponse(BaseModel):
    """文件上传成功响应"""
    success: bool
    message: str
    dataset_id: int
    dataset_name: str
    datasource_id: int
    table_name: str  # 物理表名
    row_count: int  # 导入行数
    column_count: int  # 列数
    
    class Config:
        from_attributes = True


class MultiFileUploadResponse(BaseModel):
    """多文件批量上传成功响应"""
    success: bool
    message: str
    dataset_id: int
    dataset_name: str
    tables: Dict[str, int]  # {table_name: row_count}
    total_files: int
    total_rows: int
    duckdb_path: str
    
    class Config:
        from_attributes = True


class UploadedDatasetInfo(BaseModel):
    """上传数据集信息"""
    dataset_id: int
    dataset_name: str
    file_name: str
    row_count: int
    column_count: int
    created_at: str
    status: str
    is_uploaded: bool = True  # 标识这是上传的数据集
    
    class Config:
        from_attributes = True

