"""
DuckDB 服务 - 处理多表数据的存储和查询
支持批量导入 Excel/CSV 数据，提供高性能 OLAP 查询能力
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.core.logger import get_logger

logger = get_logger(__name__)


class DuckDBService:
    """DuckDB 数据库管理服务
    
    提供以下核心功能：
    1. 为每个 Dataset 创建独立的 DuckDB 数据库
    2. 批量导入多个 DataFrame 到 DuckDB
    3. 执行 SQL 查询并返回结果
    4. 获取表的 Schema 信息和 DDL
    5. 数据采样和统计分析
    """
    
    # DuckDB 存储根目录
    STORAGE_ROOT = Path("duckdb_storage")
    
    @classmethod
    def ensure_storage_dir(cls) -> None:
        """确保存储目录存在"""
        cls.STORAGE_ROOT.mkdir(exist_ok=True, parents=True)
        logger.info(f"DuckDB storage directory ensured: {cls.STORAGE_ROOT.absolute()}")
    
    @classmethod
    def create_dataset_database(cls, dataset_id: int) -> str:
        """为每个 Dataset 创建独立的 DuckDB 数据库文件
        
        Args:
            dataset_id: 数据集 ID
            
        Returns:
            str: DuckDB 数据库文件路径
        """
        cls.ensure_storage_dir()
        db_path = cls.STORAGE_ROOT / f"dataset_{dataset_id}.db"
        
        logger.info(f"Creating DuckDB database for dataset {dataset_id} at {db_path}")
        
        # 创建连接以初始化数据库文件
        conn = duckdb.connect(str(db_path))
        conn.close()
        
        return str(db_path)
    
    @classmethod
    def import_dataframes(
        cls,
        db_path: str,
        dataframes: Dict[str, pd.DataFrame]
    ) -> Dict[str, int]:
        """批量导入多个 DataFrame 到 DuckDB
        
        Args:
            db_path: DuckDB 数据库路径
            dataframes: {table_name: DataFrame} 字典
            
        Returns:
            {table_name: row_count} 统计信息
        """
        logger.info(f"Importing {len(dataframes)} tables to DuckDB: {db_path}")
        
        conn = duckdb.connect(db_path)
        stats = {}
        
        try:
            for table_name, df in dataframes.items():
                # 清洗列名（DuckDB 要求）
                original_columns = df.columns.tolist()
                df.columns = [
                    col.replace(' ', '_')
                       .replace('-', '_')
                       .replace('.', '_')
                       .replace('(', '')
                       .replace(')', '')
                       .replace('[', '')
                       .replace(']', '')
                    for col in df.columns
                ]
                
                logger.debug(
                    f"Importing table {table_name}: {len(df)} rows, {len(df.columns)} columns",
                    extra={"original_columns": original_columns, "cleaned_columns": df.columns.tolist()}
                )
                
                # 注册 DataFrame 并创建表
                # 使用 CREATE OR REPLACE 确保可重复执行
                conn.register('temp_df', df)
                conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_df")
                conn.unregister('temp_df')
                
                stats[table_name] = len(df)
                
                logger.info(f"Successfully imported table {table_name}: {len(df)} rows")
        
        except Exception as e:
            logger.error(f"Failed to import dataframes: {e}", exc_info=True)
            raise
        finally:
            conn.close()
        
        return stats
    
    @classmethod
    def execute_query(
        cls,
        db_path: str,
        sql: str,
        read_only: bool = True
    ) -> pd.DataFrame:
        """执行 SQL 查询并返回结果
        
        Args:
            db_path: DuckDB 数据库路径
            sql: SQL 查询语句
            read_only: 是否以只读模式打开（默认 True）
            
        Returns:
            pd.DataFrame: 查询结果
        """
        logger.debug(f"Executing SQL on {db_path}: {sql[:100]}...")
        
        try:
            conn = duckdb.connect(db_path, read_only=read_only)
            result = conn.execute(sql).fetchdf()
            conn.close()
            
            logger.info(f"Query executed successfully, returned {len(result)} rows")
            return result
        
        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_table_schema(cls, db_path: str, table_name: str) -> List[Dict[str, Any]]:
        """获取表的 Schema 信息
        
        Args:
            db_path: DuckDB 数据库路径
            table_name: 表名
            
        Returns:
            List[Dict]: Schema 信息列表
            [{"name": "col1", "type": "INTEGER", "nullable": True}, ...]
        """
        logger.debug(f"Getting schema for table {table_name}")
        
        try:
            conn = duckdb.connect(db_path, read_only=True)
            result = conn.execute(f"DESCRIBE {table_name}").fetchall()
            conn.close()
            
            schema = [
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES" if len(row) > 2 else True
                }
                for row in result
            ]
            
            logger.info(f"Retrieved schema for {table_name}: {len(schema)} columns")
            return schema
        
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_table_ddl(cls, db_path: str, table_name: str) -> str:
        """获取表的 DDL（CREATE TABLE 语句）
        
        Args:
            db_path: DuckDB 数据库路径
            table_name: 表名
            
        Returns:
            str: DDL 语句
        """
        logger.debug(f"Getting DDL for table {table_name}")
        
        try:
            schema = cls.get_table_schema(db_path, table_name)
            
            # 构建 CREATE TABLE 语句
            columns_def = []
            for col in schema:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                columns_def.append(f"  {col['name']} {col['type']} {nullable}")
            
            ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(columns_def) + "\n);"
            
            logger.info(f"Generated DDL for {table_name}")
            return ddl
        
        except Exception as e:
            logger.error(f"Failed to generate DDL for {table_name}: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_table_sample(
        cls,
        db_path: str,
        table_name: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """获取表的采样数据
        
        Args:
            db_path: DuckDB 数据库路径
            table_name: 表名
            limit: 采样行数（默认 100）
            
        Returns:
            pd.DataFrame: 采样数据
        """
        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        return cls.execute_query(db_path, sql, read_only=True)
    
    @classmethod
    def get_table_statistics(
        cls,
        db_path: str,
        table_name: str
    ) -> Dict[str, Any]:
        """获取表的统计信息
        
        Args:
            db_path: DuckDB 数据库路径
            table_name: 表名
            
        Returns:
            Dict: 统计信息
            {
                "row_count": 1000,
                "column_count": 5,
                "columns": [
                    {
                        "name": "col1",
                        "type": "INTEGER",
                        "null_count": 0,
                        "distinct_count": 100
                    },
                    ...
                ]
            }
        """
        logger.debug(f"Getting statistics for table {table_name}")
        
        try:
            conn = duckdb.connect(db_path, read_only=True)
            
            # 获取行数
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # 获取 Schema
            schema = cls.get_table_schema(db_path, table_name)
            
            # 为每列获取统计信息
            column_stats = []
            for col in schema:
                col_name = col['name']
                
                # NULL 值数量
                null_count = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                ).fetchone()[0]
                
                # 唯一值数量（限制扫描提高性能）
                distinct_count = conn.execute(
                    f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name}"
                ).fetchone()[0]
                
                column_stats.append({
                    "name": col_name,
                    "type": col['type'],
                    "null_count": null_count,
                    "null_ratio": null_count / row_count if row_count > 0 else 0,
                    "distinct_count": distinct_count
                })
            
            conn.close()
            
            statistics = {
                "row_count": row_count,
                "column_count": len(schema),
                "columns": column_stats
            }
            
            logger.info(f"Retrieved statistics for {table_name}: {row_count} rows, {len(schema)} columns")
            return statistics
        
        except Exception as e:
            logger.error(f"Failed to get statistics for {table_name}: {e}", exc_info=True)
            raise
    
    @classmethod
    def list_tables(cls, db_path: str) -> List[str]:
        """列出数据库中的所有表
        
        Args:
            db_path: DuckDB 数据库路径
            
        Returns:
            List[str]: 表名列表
        """
        try:
            conn = duckdb.connect(db_path, read_only=True)
            result = conn.execute("SHOW TABLES").fetchall()
            conn.close()
            
            tables = [row[0] for row in result]
            logger.info(f"Found {len(tables)} tables in {db_path}")
            return tables
        
        except Exception as e:
            logger.error(f"Failed to list tables: {e}", exc_info=True)
            raise
    
    @classmethod
    def table_exists(cls, db_path: str, table_name: str) -> bool:
        """检查表是否存在
        
        Args:
            db_path: DuckDB 数据库路径
            table_name: 表名
            
        Returns:
            bool: 表是否存在
        """
        try:
            tables = cls.list_tables(db_path)
            return table_name in tables
        except Exception:
            return False
    
    @classmethod
    def delete_database(cls, db_path: str) -> bool:
        """删除 DuckDB 数据库文件
        
        Args:
            db_path: DuckDB 数据库路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink()
                logger.info(f"Deleted DuckDB database: {db_path}")
                return True
            else:
                logger.warning(f"DuckDB database not found: {db_path}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to delete DuckDB database {db_path}: {e}", exc_info=True)
            return False
