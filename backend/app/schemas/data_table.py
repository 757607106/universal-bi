"""
数据表管理相关的Pydantic Schema定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


# ============ 文件夹相关 Schema ============

class FolderBase(BaseModel):
    """文件夹基础模型"""
    name: str = Field(..., description="文件夹名称")
    parent_id: Optional[int] = Field(None, description="父文件夹ID")


class FolderCreate(FolderBase):
    """创建文件夹请求"""
    pass


class FolderUpdate(BaseModel):
    """更新文件夹请求"""
    name: Optional[str] = Field(None, description="文件夹名称")
    parent_id: Optional[int] = Field(None, description="父文件夹ID")


class FolderResponse(FolderBase):
    """文件夹响应"""
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 表字段相关 Schema ============

class TableFieldConfig(BaseModel):
    """表字段配置"""
    field_name: str = Field(..., description="字段值（物理字段名）")
    field_display_name: str = Field(..., description="字段中文名")
    field_type: str = Field(..., description="字段类型: text, number, datetime, geo")
    date_format: Optional[str] = Field(None, description="时间格式")
    null_display: str = Field("—", description="空值展示")
    description: Optional[str] = Field(None, description="字段备注")
    is_selected: bool = Field(True, description="是否选中")
    sort_order: int = Field(0, description="排序顺序")


class TableFieldResponse(TableFieldConfig):
    """表字段响应"""
    id: int
    data_table_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 数据表相关 Schema ============

class DataTableBase(BaseModel):
    """数据表基础模型"""
    display_name: str = Field(..., description="显示名称")
    datasource_id: int = Field(..., description="数据源ID")
    folder_id: Optional[int] = Field(None, description="所属文件夹ID")
    description: Optional[str] = Field(None, description="表备注")


class DataTableCreate(DataTableBase):
    """创建数据表请求"""
    creation_method: str = Field(..., description="建表方式: excel_upload, datasource_table")
    physical_table_name: Optional[str] = Field(None, description="物理表名（可选，系统自动生成）")
    source_table_name: Optional[str] = Field(None, description="源表名（从数据源选择时使用）")
    file_content: Optional[bytes] = Field(None, description="Excel文件内容（上传时使用）")
    filename: Optional[str] = Field(None, description="文件名（上传时使用）")
    fields: Optional[List[TableFieldConfig]] = Field(None, description="字段配置列表")


class DataTableUpdate(BaseModel):
    """更新数据表请求"""
    display_name: Optional[str] = Field(None, description="显示名称")
    folder_id: Optional[int] = Field(None, description="所属文件夹ID")
    description: Optional[str] = Field(None, description="表备注")
    status: Optional[str] = Field(None, description="状态")


class DataTableResponse(DataTableBase):
    """数据表响应"""
    id: int
    physical_table_name: str
    creation_method: str
    status: str
    row_count: int
    column_count: int
    owner_id: Optional[int] = None
    modifier_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataTableWithFields(DataTableResponse):
    """包含字段列表的数据表响应"""
    fields: List[TableFieldResponse] = []

    class Config:
        from_attributes = True


# ============ Excel预览相关 Schema ============

class ExcelFieldPreview(BaseModel):
    """Excel字段预览"""
    field_name: str = Field(..., description="字段名")
    field_display_name: str = Field(..., description="字段显示名")
    field_type: str = Field(..., description="推断的字段类型")
    sample_values: List[Any] = Field(default_factory=list, description="示例值（前5个）")


class ExcelPreviewResponse(BaseModel):
    """Excel预览响应"""
    filename: str = Field(..., description="文件名")
    row_count: int = Field(..., description="总行数")
    column_count: int = Field(..., description="总列数")
    fields: List[ExcelFieldPreview] = Field(..., description="字段列表")
    preview_data: List[Dict[str, Any]] = Field(..., description="预览数据（前20行）")


# ============ 字段更新相关 Schema ============

class UpdateFieldsRequest(BaseModel):
    """更新字段配置请求"""
    fields: List[TableFieldConfig] = Field(..., description="字段配置列表")


# ============ 数据查询相关 Schema ============

class DataQueryRequest(BaseModel):
    """数据查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class DataQueryResponse(BaseModel):
    """数据查询响应"""
    total: int = Field(..., description="总行数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    data: List[Dict[str, Any]] = Field(..., description="数据列表")
    columns: List[TableFieldResponse] = Field(..., description="列配置")
