"""
数据表管理服务
处理数据表的创建、更新、删除等业务逻辑
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, inspect, text
from sqlalchemy.orm import Session

from app.models.data_table import Folder, DataTable, TableField
from app.models.metadata import DataSource, User
from app.schemas.data_table import TableFieldConfig
from app.services.file_etl import FileETLService
from app.core.security import decrypt_password
from app.core.logger import get_logger

logger = get_logger(__name__)


class DataTableService:
    """数据表管理服务类"""
    
    @staticmethod
    def create_data_table_from_excel(
        display_name: str,
        file_content: bytes,
        filename: str,
        fields_config: List[TableFieldConfig],
        datasource_id: int,
        folder_id: Optional[int],
        description: Optional[str],
        user: User,
        db_session: Session
    ) -> DataTable:
        """
        从Excel创建数据表
        
        Args:
            display_name: 显示名称
            file_content: 文件内容
            filename: 文件名
            fields_config: 字段配置列表
            datasource_id: 数据源ID
            folder_id: 文件夹ID
            description: 表备注
            user: 当前用户
            db_session: 数据库会话
            
        Returns:
            DataTable: 创建的数据表对象
        """
        try:
            # 1. 解析Excel
            df, _ = FileETLService.parse_file_with_types(file_content, filename)
            
            # 2. 获取数据源
            datasource = db_session.query(DataSource).filter(
                DataSource.id == datasource_id
            ).first()
            if not datasource:
                raise ValueError(f"数据源不存在: {datasource_id}")
            
            # 3. 生成物理表名
            physical_table_name = FileETLService.generate_table_name(user.id, filename)
            physical_table_name = f"dt_{physical_table_name}"  # 加上dt前缀区分
            
            # 4. 根据字段配置过滤DataFrame
            selected_fields = [f for f in fields_config if f.is_selected]
            selected_columns = [f.field_name for f in selected_fields]
            df_filtered = df[selected_columns]
            
            # 5. 写入数据库
            row_count = FileETLService.write_to_database(
                df=df_filtered,
                table_name=physical_table_name,
                datasource=datasource,
                db_session=db_session
            )
            
            # 6. 创建DataTable记录
            data_table = DataTable(
                display_name=display_name,
                physical_table_name=physical_table_name,
                datasource_id=datasource_id,
                folder_id=folder_id,
                description=description,
                creation_method='excel_upload',
                status='active',
                row_count=row_count,
                column_count=len(selected_columns),
                owner_id=user.id,
                modifier_id=user.id
            )
            db_session.add(data_table)
            db_session.flush()  # 获取ID
            
            # 7. 创建字段配置记录
            for field_config in selected_fields:
                table_field = TableField(
                    data_table_id=data_table.id,
                    field_name=field_config.field_name,
                    field_display_name=field_config.field_display_name,
                    field_type=field_config.field_type,
                    date_format=field_config.date_format,
                    null_display=field_config.null_display,
                    description=field_config.description,
                    is_selected=field_config.is_selected,
                    sort_order=field_config.sort_order
                )
                db_session.add(table_field)
            
            db_session.commit()
            db_session.refresh(data_table)
            
            logger.info(
                "Data table created from Excel",
                data_table_id=data_table.id,
                physical_table_name=physical_table_name,
                user_id=user.id
            )
            
            return data_table
            
        except Exception as e:
            db_session.rollback()
            logger.error(
                "Failed to create data table from Excel",
                error=str(e),
                user_id=user.id,
                exc_info=True
            )
            raise ValueError(f"创建数据表失败: {str(e)}")
    
    @staticmethod
    def create_data_table_from_datasource(
        display_name: str,
        source_table_name: str,
        fields_config: List[TableFieldConfig],
        datasource_id: int,
        folder_id: Optional[int],
        description: Optional[str],
        user: User,
        db_session: Session
    ) -> DataTable:
        """
        从数据源表创建数据表
        
        Args:
            display_name: 显示名称
            source_table_name: 源表名
            fields_config: 字段配置列表
            datasource_id: 数据源ID
            folder_id: 文件夹ID
            description: 表备注
            user: 当前用户
            db_session: 数据库会话
            
        Returns:
            DataTable: 创建的数据表对象
        """
        try:
            # 1. 获取数据源
            datasource = db_session.query(DataSource).filter(
                DataSource.id == datasource_id
            ).first()
            if not datasource:
                raise ValueError(f"数据源不存在: {datasource_id}")
            
            # 2. 连接到源数据库
            password = decrypt_password(datasource.password_encrypted)
            db_url = f"{datasource.type}+pymysql://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?charset=utf8mb4"
            engine = create_engine(db_url)
            
            # 3. 检查源表是否存在
            inspector = inspect(engine)
            if source_table_name not in inspector.get_table_names():
                raise ValueError(f"源表不存在: {source_table_name}")
            
            # 4. 获取行数和列数
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {source_table_name}"))
                row_count = result.scalar()
            
            selected_fields = [f for f in fields_config if f.is_selected]
            column_count = len(selected_fields)
            
            # 5. 创建DataTable记录（直接引用源表，不复制数据）
            data_table = DataTable(
                display_name=display_name,
                physical_table_name=source_table_name,  # 直接使用源表名
                datasource_id=datasource_id,
                folder_id=folder_id,
                description=description,
                creation_method='datasource_table',
                status='active',
                row_count=row_count,
                column_count=column_count,
                owner_id=user.id,
                modifier_id=user.id
            )
            db_session.add(data_table)
            db_session.flush()
            
            # 6. 创建字段配置记录
            for field_config in selected_fields:
                table_field = TableField(
                    data_table_id=data_table.id,
                    field_name=field_config.field_name,
                    field_display_name=field_config.field_display_name,
                    field_type=field_config.field_type,
                    date_format=field_config.date_format,
                    null_display=field_config.null_display,
                    description=field_config.description,
                    is_selected=field_config.is_selected,
                    sort_order=field_config.sort_order
                )
                db_session.add(table_field)
            
            db_session.commit()
            db_session.refresh(data_table)
            
            logger.info(
                "Data table created from datasource",
                data_table_id=data_table.id,
                source_table_name=source_table_name,
                user_id=user.id
            )
            
            return data_table
            
        except Exception as e:
            db_session.rollback()
            logger.error(
                "Failed to create data table from datasource",
                error=str(e),
                user_id=user.id,
                exc_info=True
            )
            raise ValueError(f"创建数据表失败: {str(e)}")
    
    @staticmethod
    def update_field_config(
        data_table_id: int,
        fields_config: List[TableFieldConfig],
        user: User,
        db_session: Session
    ) -> DataTable:
        """
        更新字段配置
        
        Args:
            data_table_id: 数据表ID
            fields_config: 字段配置列表
            user: 当前用户
            db_session: 数据库会话
            
        Returns:
            DataTable: 更新后的数据表对象
        """
        try:
            # 1. 获取数据表
            data_table = db_session.query(DataTable).filter(
                DataTable.id == data_table_id
            ).first()
            if not data_table:
                raise ValueError(f"数据表不存在: {data_table_id}")
            
            # 2. 删除旧的字段配置
            db_session.query(TableField).filter(
                TableField.data_table_id == data_table_id
            ).delete()
            
            # 3. 创建新的字段配置
            for field_config in fields_config:
                table_field = TableField(
                    data_table_id=data_table_id,
                    field_name=field_config.field_name,
                    field_display_name=field_config.field_display_name,
                    field_type=field_config.field_type,
                    date_format=field_config.date_format,
                    null_display=field_config.null_display,
                    description=field_config.description,
                    is_selected=field_config.is_selected,
                    sort_order=field_config.sort_order
                )
                db_session.add(table_field)
            
            # 4. 更新修改人和列数
            data_table.modifier_id = user.id
            data_table.column_count = len([f for f in fields_config if f.is_selected])
            data_table.updated_at = datetime.utcnow()
            
            db_session.commit()
            db_session.refresh(data_table)
            
            logger.info(
                "Field config updated",
                data_table_id=data_table_id,
                user_id=user.id
            )
            
            return data_table
            
        except Exception as e:
            db_session.rollback()
            logger.error(
                "Failed to update field config",
                data_table_id=data_table_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"更新字段配置失败: {str(e)}")
    
    @staticmethod
    def query_data_table(
        data_table_id: int,
        page: int,
        page_size: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        查询数据表数据
        
        Args:
            data_table_id: 数据表ID
            page: 页码
            page_size: 每页数量
            db_session: 数据库会话
            
        Returns:
            dict: 查询结果
        """
        try:
            # 1. 获取数据表信息
            data_table = db_session.query(DataTable).filter(
                DataTable.id == data_table_id
            ).first()
            if not data_table:
                raise ValueError(f"数据表不存在: {data_table_id}")
            
            # 2. 获取数据源
            datasource = data_table.datasource
            password = decrypt_password(datasource.password_encrypted)
            db_url = f"{datasource.type}+pymysql://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?charset=utf8mb4"
            engine = create_engine(db_url)
            
            # 3. 获取字段配置
            fields = db_session.query(TableField).filter(
                TableField.data_table_id == data_table_id,
                TableField.is_selected == True
            ).order_by(TableField.sort_order).all()
            
            selected_columns = [f.field_name for f in fields]
            
            # 4. 查询数据
            offset = (page - 1) * page_size
            query_sql = f"SELECT {','.join(selected_columns)} FROM {data_table.physical_table_name} LIMIT {page_size} OFFSET {offset}"
            
            with engine.connect() as conn:
                result = conn.execute(text(query_sql))
                rows = result.fetchall()
                
                # 转换为字典列表
                data = []
                for row in rows:
                    row_dict = {}
                    for idx, col_name in enumerate(selected_columns):
                        row_dict[col_name] = row[idx]
                    data.append(row_dict)
            
            return {
                'total': data_table.row_count,
                'page': page,
                'page_size': page_size,
                'data': data,
                'columns': fields
            }
            
        except Exception as e:
            logger.error(
                "Failed to query data table",
                data_table_id=data_table_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"查询数据表失败: {str(e)}")
    
    @staticmethod
    def delete_data_table(
        data_table_id: int,
        user: User,
        db_session: Session
    ) -> bool:
        """
        删除数据表（包括物理表）
        
        Args:
            data_table_id: 数据表ID
            user: 当前用户
            db_session: 数据库会话
            
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 获取数据表
            data_table = db_session.query(DataTable).filter(
                DataTable.id == data_table_id
            ).first()
            if not data_table:
                raise ValueError(f"数据表不存在: {data_table_id}")
            
            # 2. 如果是Excel上传创建的，删除物理表
            if data_table.creation_method == 'excel_upload':
                datasource = data_table.datasource
                password = decrypt_password(datasource.password_encrypted)
                db_url = f"{datasource.type}+pymysql://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?charset=utf8mb4"
                engine = create_engine(db_url)
                
                with engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {data_table.physical_table_name}"))
                    conn.commit()
                
                logger.info(
                    "Physical table dropped",
                    physical_table_name=data_table.physical_table_name
                )
            
            # 3. 删除数据表记录（字段配置会级联删除）
            db_session.delete(data_table)
            db_session.commit()
            
            logger.info(
                "Data table deleted",
                data_table_id=data_table_id,
                user_id=user.id
            )
            
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error(
                "Failed to delete data table",
                data_table_id=data_table_id,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"删除数据表失败: {str(e)}")
