"""
数据表管理模型
包含文件夹、数据表、表字段配置等模型定义
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from datetime import datetime


class Folder(Base):
    """文件夹模型 - 用于组织数据表"""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="文件夹名称")
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True, comment="父文件夹ID")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所有者ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    parent = relationship("Folder", remote_side=[id], backref="children")
    owner = relationship("User")
    data_tables = relationship("DataTable", back_populates="folder", cascade="all, delete-orphan")


class DataTable(Base):
    """数据表模型 - 存储数据表的元数据"""
    __tablename__ = "data_tables"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), nullable=False, comment="显示名称")
    physical_table_name = Column(String(255), nullable=False, index=True, comment="物理表名")
    datasource_id = Column(Integer, ForeignKey("datasources.id"), nullable=False, comment="数据源ID")
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, comment="所属文件夹ID")
    description = Column(Text, nullable=True, comment="表备注")
    creation_method = Column(String(50), nullable=False, comment="建表方式: excel_upload, datasource_table")
    status = Column(String(50), default="active", comment="状态: active, archived")
    row_count = Column(Integer, default=0, comment="行数")
    column_count = Column(Integer, default=0, comment="列数")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建人ID")
    modifier_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="修改人ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    datasource = relationship("DataSource")
    folder = relationship("Folder", back_populates="data_tables")
    owner = relationship("User", foreign_keys=[owner_id])
    modifier = relationship("User", foreign_keys=[modifier_id])
    fields = relationship("TableField", back_populates="data_table", cascade="all, delete-orphan")


class TableField(Base):
    """表字段配置模型 - 存储字段的配置信息"""
    __tablename__ = "table_fields"

    id = Column(Integer, primary_key=True, index=True)
    data_table_id = Column(Integer, ForeignKey("data_tables.id"), nullable=False, comment="数据表ID")
    field_name = Column(String(255), nullable=False, comment="字段值（物理字段名）")
    field_display_name = Column(String(255), nullable=False, comment="字段中文名")
    field_type = Column(String(50), nullable=False, comment="字段类型: text, number, datetime, geo")
    date_format = Column(String(50), nullable=True, comment="时间格式（如YYYY-MM-DD）")
    null_display = Column(String(50), default="—", comment="空值展示")
    description = Column(Text, nullable=True, comment="字段备注")
    is_selected = Column(Boolean, default=True, comment="是否选中")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    data_table = relationship("DataTable", back_populates="fields")
