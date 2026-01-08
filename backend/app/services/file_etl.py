"""
文件ETL服务 - 处理Excel/CSV文件的上传、解析和入库
"""
import pandas as pd
import io
from typing import Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text, inspect
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logger import get_logger
from app.models.metadata import DataSource, User

logger = get_logger(__name__)


class FileETLService:
    """文件ETL服务类"""
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    # 行数限制
    MAX_ROWS = 50000
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> None:
        """
        验证文件格式和大小
        
        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            
        Raises:
            ValueError: 如果文件格式或大小不符合要求
        """
        # 检查文件扩展名
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext not in FileETLService.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式。支持的格式: {', '.join(FileETLService.SUPPORTED_EXTENSIONS)}")
        
        # 检查文件大小
        if file_size > FileETLService.MAX_FILE_SIZE:
            max_mb = FileETLService.MAX_FILE_SIZE / (1024 * 1024)
            raise ValueError(f"文件大小超过限制。最大允许: {max_mb}MB")
    
    @staticmethod
    def parse_file(file_content: bytes, filename: str) -> pd.DataFrame:
        """
        解析Excel或CSV文件为DataFrame
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            
        Returns:
            pd.DataFrame: 解析后的数据框
            
        Raises:
            ValueError: 如果文件解析失败或行数超过限制
        """
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            # 创建BytesIO对象
            file_like = io.BytesIO(file_content)
            
            # 根据文件类型解析
            if ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_like, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
            elif ext == '.csv':
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                    try:
                        file_like.seek(0)
                        df = pd.read_csv(file_like, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("无法解码CSV文件，请确保文件编码正确")
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
            
            # 检查DataFrame是否为空
            if df.empty:
                raise ValueError("文件内容为空")
            
            # 检查行数
            if len(df) > FileETLService.MAX_ROWS:
                raise ValueError(f"文件行数超过限制。最大允许: {FileETLService.MAX_ROWS} 行，当前: {len(df)} 行")
            
            # 清理列名（去除空格，替换特殊字符）
            df.columns = [FileETLService._clean_column_name(col) for col in df.columns]
            
            # 处理缺失值
            df = df.fillna('')
            
            logger.info(
                "File parsed successfully",
                filename=filename,
                rows=len(df),
                columns=len(df.columns)
            )
            
            return df
            
        except Exception as e:
            logger.error(
                "File parsing failed",
                filename=filename,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"文件解析失败: {str(e)}")
    
    @staticmethod
    def _clean_column_name(col_name: str) -> str:
        """
        清理列名，确保符合SQL标准
        
        Args:
            col_name: 原始列名
            
        Returns:
            str: 清理后的列名
        """
        # 转换为字符串
        col_name = str(col_name).strip()
        
        # 替换空格和特殊字符为下划线
        import re
        col_name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', col_name)
        
        # 如果以数字开头，添加前缀
        if col_name and col_name[0].isdigit():
            col_name = 'col_' + col_name
        
        # 如果为空，使用默认名称
        if not col_name:
            col_name = 'column'
        
        return col_name
    
    @staticmethod
    def infer_sql_type(series: pd.Series) -> Any:
        """
        推断Pandas列的SQL数据类型
        
        Args:
            series: Pandas Series
            
        Returns:
            SQLAlchemy类型对象
        """
        from sqlalchemy import Integer, Float, Boolean, DateTime, Text, String
        
        # 获取非空数据用于类型推断
        non_null = series.dropna()
        if len(non_null) == 0:
            return Text  # 全空列默认Text
        
        dtype = series.dtype
        
        # 数值类型
        if pd.api.types.is_integer_dtype(dtype):
            return Integer
        elif pd.api.types.is_float_dtype(dtype):
            return Float
        elif pd.api.types.is_bool_dtype(dtype):
            return Boolean
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return DateTime
        else:
            # 字符串类型 - 检查最大长度
            max_length = non_null.astype(str).str.len().max()
            if max_length > 500:
                return Text
            else:
                return String(500)
    
    @staticmethod
    def infer_field_type(series: pd.Series) -> str:
        """
        推断字段类型（用于前端展示）
        
        Args:
            series: Pandas Series
            
        Returns:
            str: 字段类型 (text, number, datetime, geo)
        """
        # 1. 检查地理类型（基于字段名）
        col_name_lower = str(series.name).lower()
        geo_keywords = ['经度', 'longitude', 'lng', '纬度', 'latitude', 'lat', '坐标', 'coord']
        if any(keyword in col_name_lower for keyword in geo_keywords):
            return 'geo'
        
        # 2. 检查数值类型
        if pd.api.types.is_numeric_dtype(series):
            return 'number'
        
        # 3. 检查时间类型
        if pd.api.types.is_datetime64_any_dtype(series):
            return 'datetime'
        
        # 4. 尝试解析时间类型（字符串）
        if series.dtype == 'object':
            non_null = series.dropna()
            if len(non_null) > 0:
                # 取前5个样本尝试解析
                sample = non_null.iloc[:min(5, len(non_null))]
                try:
                    for val in sample:
                        if val:
                            pd.to_datetime(str(val))
                    # 如果全部解析成功，认为是时间类型
                    return 'datetime'
                except:
                    pass
        
        # 5. 默认为文本类型
        return 'text'
    
    @staticmethod
    def parse_file_with_types(file_content: bytes, filename: str) -> tuple:
        """
        解析文件并推断字段类型
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            
        Returns:
            tuple: (DataFrame, List[字段信息字典])
        """
        # 先解析文件
        df = FileETLService.parse_file(file_content, filename)
        
        # 推断每个字段的类型
        fields_info = []
        for idx, col_name in enumerate(df.columns):
            series = df[col_name]
            field_type = FileETLService.infer_field_type(series)
            
            # 获取示例值（前5个非空值）
            non_null = series.dropna()
            sample_values = non_null.iloc[:min(5, len(non_null))].tolist()
            
            field_info = {
                'field_name': col_name,
                'field_display_name': col_name,  # 默认中文名与字段名相同
                'field_type': field_type,
                'date_format': 'YYYY-MM-DD' if field_type == 'datetime' else None,
                'null_display': '—',
                'description': '',
                'is_selected': True,
                'sort_order': idx,
                'sample_values': sample_values
            }
            fields_info.append(field_info)
        
        return df, fields_info
    
    @staticmethod
    def preview_excel(file_content: bytes, filename: str) -> dict:
        """
        预览Excel文件（不写入数据库）
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            
        Returns:
            dict: 预览信息
        """
        # 解析文件和字段类型
        df, fields_info = FileETLService.parse_file_with_types(file_content, filename)
        
        # 获取前20行数据用于预览
        preview_rows = min(20, len(df))
        preview_data = df.head(preview_rows).to_dict('records')
        
        return {
            'filename': filename,
            'row_count': len(df),
            'column_count': len(df.columns),
            'fields': fields_info,
            'preview_data': preview_data
        }
    
    @staticmethod
    def create_upload_datasource(
        db: Session,
        user: User,
        datasource_name: str = "Upload DataSource"
    ) -> DataSource:
        """
        创建或获取用于存储上传文件的数据源
        
        Args:
            db: 数据库会话
            user: 当前用户
            datasource_name: 数据源名称
            
        Returns:
            DataSource: 数据源对象
        """
        from app.core.security import encrypt_password
        
        # 查找是否已存在该用户的上传数据源
        existing_ds = db.query(DataSource).filter(
            DataSource.owner_id == user.id,
            DataSource.type == "upload",
            DataSource.name == datasource_name
        ).first()
        
        if existing_ds:
            return existing_ds
        
        # 创建新的上传数据源（使用主数据库）
        # 解析主数据库URI
        from sqlalchemy.engine.url import make_url
        db_url = make_url(settings.SQLALCHEMY_DATABASE_URI)
        
        # 从数据库URI推断实际的数据库类型
        db_type = "mysql"  # 默认
        if db_url.drivername:
            if "postgresql" in db_url.drivername:
                db_type = "postgresql"
            elif "mysql" in db_url.drivername:
                db_type = "mysql"
            elif "sqlite" in db_url.drivername:
                db_type = "sqlite"
        
        # 创建数据源记录 - 使用实际数据库类型而不是"upload"
        datasource = DataSource(
            name=datasource_name,
            type=db_type,  # 使用实际数据库类型（mysql/postgresql/sqlite）
            host=db_url.host or "localhost",
            port=db_url.port or (3306 if db_type == "mysql" else 5432),
            username=db_url.username or "root",
            password_encrypted=encrypt_password(db_url.password or ""),
            database_name=db_url.database or "universal_bi",
            owner_id=user.id
        )
        
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        logger.info(
            "Created upload datasource",
            datasource_id=datasource.id,
            user_id=user.id
        )
        
        return datasource
    
    @staticmethod
    def write_to_database(
        df: pd.DataFrame,
        table_name: str,
        datasource: DataSource,
        db_session: Session
    ) -> int:
        """
        将DataFrame写入数据库
        
        Args:
            df: 数据框
            table_name: 目标表名
            datasource: 数据源对象
            db_session: 数据库会话（用于解密密码）
            
        Returns:
            int: 写入的行数
            
        Raises:
            ValueError: 如果数据库写入失败
        """
        from app.core.security import decrypt_password
        
        try:
            # 解密数据库密码
            password = decrypt_password(datasource.password_encrypted)
            
            # 构建数据库连接字符串
            if datasource.type == "upload":
                # 上传类型使用主数据库
                db_url = settings.SQLALCHEMY_DATABASE_URI
            else:
                # 其他类型构建连接
                db_url = f"mysql+pymysql://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?charset=utf8mb4"
            
            # 创建引擎
            engine = create_engine(db_url)
            
            # 创建表结构
            metadata = MetaData()
            columns = [Column('id', Integer, primary_key=True, autoincrement=True)]
            
            for col_name in df.columns:
                sql_type = FileETLService.infer_sql_type(df[col_name])
                columns.append(Column(col_name, sql_type, nullable=True))
            
            table = Table(table_name, metadata, *columns, extend_existing=True)
            
            # 创建表
            metadata.create_all(engine)
            
            # 写入数据
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            row_count = len(df)
            
            logger.info(
                "Data written to database",
                table_name=table_name,
                rows=row_count,
                columns=len(df.columns)
            )
            
            return row_count
            
        except Exception as e:
            logger.error(
                "Database write failed",
                table_name=table_name,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"数据库写入失败: {str(e)}")
    
    @staticmethod
    def generate_table_name(user_id: int, filename: str) -> str:
        """
        生成唯一的物理表名
        
        Args:
            user_id: 用户ID
            filename: 原始文件名
            
        Returns:
            str: 表名
        """
        import os
        import re
        
        # 提取文件名（不含扩展名）
        base_name = os.path.splitext(filename)[0]
        
        # 清理文件名
        clean_name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', base_name)
        clean_name = clean_name[:30]  # 限制长度
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 组合表名: upload_用户ID_文件名_时间戳
        table_name = f"upload_{user_id}_{clean_name}_{timestamp}"
        
        return table_name.lower()

