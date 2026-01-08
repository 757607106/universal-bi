"""
File Handler Utility

Handles file uploads (CSV, Excel) and converts them to pandas DataFrames.
Provides utilities for sanitizing column names for SQL compatibility.
"""

import re
import pandas as pd
from fastapi import UploadFile, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def read_file_to_df(file: UploadFile) -> pd.DataFrame:
    """
    Read uploaded file (CSV or Excel) to pandas DataFrame.
    
    Supports:
    - CSV files (.csv) with automatic encoding detection
    - Excel files (.xlsx, .xls)
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        pd.DataFrame: Parsed DataFrame
        
    Raises:
        HTTPException: If file format is unsupported or parsing fails
    """
    filename = file.filename or ""
    file_ext = filename.lower().split('.')[-1]
    
    try:
        # Read file content
        file_content = file.file.read()
        
        if file_ext == 'csv':
            # Try multiple encodings for CSV
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    import io
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                    logger.info(f"Successfully read CSV with encoding: {encoding}")
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                raise HTTPException(
                    status_code=400,
                    detail="无法解析 CSV 文件，请检查文件编码（支持 UTF-8, GBK, GB2312）"
                )
                
        elif file_ext in ['xlsx', 'xls']:
            import io
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl' if file_ext == 'xlsx' else None)
            logger.info(f"Successfully read Excel file: {filename}")
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}。仅支持 .csv, .xlsx, .xls"
            )
        
        # Validate DataFrame
        if df.empty:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        logger.info(f"Loaded DataFrame: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file {filename}: {e}")
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")
    finally:
        # Reset file pointer
        file.file.seek(0)


def sanitize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize DataFrame column names for SQL compatibility.
    
    Rules:
    1. Remove special characters (except underscore)
    2. Replace spaces and dashes with underscore
    3. Convert to lowercase
    4. Ensure column names start with letter or underscore
    5. Handle duplicate column names by appending suffix
    
    Args:
        df: Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with sanitized column names
    """
    new_columns = []
    seen_columns = {}
    
    for col in df.columns:
        # Convert to string
        col_str = str(col)
        
        # Replace spaces and dashes with underscore
        sanitized = col_str.replace(' ', '_').replace('-', '_')
        
        # Remove special characters (keep alphanumeric, underscore, and Chinese characters)
        sanitized = re.sub(r'[^\w\u4e00-\u9fff]', '', sanitized)
        
        # Convert to lowercase (only ASCII letters)
        sanitized = ''.join(
            c.lower() if c.isascii() and c.isalpha() else c 
            for c in sanitized
        )
        
        # Ensure starts with letter or underscore
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = '_' + sanitized
        
        # Handle empty column name
        if not sanitized:
            sanitized = 'column'
        
        # Handle duplicate columns
        if sanitized in seen_columns:
            seen_columns[sanitized] += 1
            sanitized = f"{sanitized}_{seen_columns[sanitized]}"
        else:
            seen_columns[sanitized] = 0
        
        new_columns.append(sanitized)
    
    # Update DataFrame columns
    df.columns = new_columns
    logger.info(f"Sanitized column names: {list(df.columns)}")
    
    return df


def infer_sql_types(df: pd.DataFrame) -> dict[str, str]:
    """
    Infer SQL data types from DataFrame columns.
    
    Args:
        df: Input DataFrame
        
    Returns:
        dict: Mapping of column name to SQL type
    """
    type_mapping = {}
    
    for col in df.columns:
        dtype = df[col].dtype
        
        if pd.api.types.is_integer_dtype(dtype):
            type_mapping[col] = 'INTEGER'
        elif pd.api.types.is_float_dtype(dtype):
            type_mapping[col] = 'FLOAT'
        elif pd.api.types.is_bool_dtype(dtype):
            type_mapping[col] = 'BOOLEAN'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            type_mapping[col] = 'TIMESTAMP'
        else:
            # Default to VARCHAR for string/object types
            max_length = df[col].astype(str).str.len().max()
            # Cap at 1000 characters for VARCHAR
            varchar_length = min(max_length if pd.notna(max_length) else 255, 1000)
            type_mapping[col] = f'VARCHAR({varchar_length})'
    
    return type_mapping
