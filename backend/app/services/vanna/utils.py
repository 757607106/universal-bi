"""
Vanna 工具方法

包含 SQL 清理、验证、图表推断等工具函数。
"""

import re
import pandas as pd
from datetime import datetime, date
from decimal import Decimal


def infer_chart_type(df: pd.DataFrame) -> str:
    """
    Infer the most suitable chart type based on DataFrame structure.

    Args:
        df: DataFrame to analyze

    Returns:
        str: Chart type ('line', 'bar', 'pie', or 'table')
    """
    if df is None or df.empty:
        return "table"

    # Get column types
    lower_cols = [str(c).lower() for c in df.columns]
    has_date = any(x in c for c in lower_cols for x in ['date', 'time', 'year', 'month', 'day'])

    # Check data types
    dtypes = df.dtypes.values
    has_num = any(pd.api.types.is_numeric_dtype(t) for t in dtypes)
    has_str = any(pd.api.types.is_string_dtype(t) or pd.api.types.is_object_dtype(t) or pd.api.types.is_datetime64_any_dtype(t) for t in dtypes)

    # Decision logic
    if len(df.columns) == 2 and has_date:
        return "line"
    elif len(df.columns) == 2 and has_num and has_str:
        # Could be pie chart if reasonable number of categories
        if len(df) <= 10:
            return "pie"
        return "bar"
    elif len(df.columns) >= 2 and has_num and has_str:
        return "bar"
    else:
        return "table"


def serialize_dataframe(df: pd.DataFrame) -> list:
    """
    Serialize DataFrame to JSON-compatible format.

    Args:
        df: DataFrame to serialize

    Returns:
        list: List of dictionaries with serialized values
    """
    def serialize(obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    rows = df.to_dict(orient='records')
    cleaned_rows = []
    for row in rows:
        new_row = {k: serialize(v) for k, v in row.items()}
        cleaned_rows.append(new_row)

    return cleaned_rows


def remove_intermediate_marker(response: str) -> str:
    """
    Remove 'intermediate_sql' marker from LLM response.

    Args:
        response: Raw LLM response that may contain 'intermediate_sql' marker

    Returns:
        str: Cleaned response with marker removed
    """
    if not response or not isinstance(response, str):
        return response

    # Remove 'intermediate_sql' marker (case insensitive)
    # Pattern: intermediate_sql\n or intermediate sql\n or intermediate_sql:
    cleaned = re.sub(r'intermediate[_\s]?sql[:\s]*\n?', '', response, flags=re.IGNORECASE)

    return cleaned.strip()


def is_valid_sql(sql: str) -> bool:
    """
    Check if the string is a valid SQL query.

    Args:
        sql: String to validate

    Returns:
        bool: True if valid SQL, False otherwise
    """
    if not sql or not isinstance(sql, str):
        return False

    sql_upper = sql.upper().strip()

    # Must contain SELECT and FROM
    # Simple validation - just check for basic SQL structure
    has_select = 'SELECT' in sql_upper
    has_from = 'FROM' in sql_upper

    # Check it's not just text with these words
    # Valid SQL should have SELECT near the beginning
    if has_select and has_from:
        select_pos = sql_upper.find('SELECT')
        # SELECT should be within first 50 characters (allowing for comments/whitespace)
        if select_pos < 50:
            return True

    return False


def ensure_clean_sql(sql: str) -> str:
    """
    Ensure SQL is completely clean before execution.
    Removes all markdown, intermediate markers, and extra whitespace.

    Args:
        sql: SQL string to clean

    Returns:
        str: Cleaned SQL ready for execution
    """
    if not sql or not isinstance(sql, str):
        return sql

    # Remove markdown code blocks
    sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'```\s*', '', sql)

    # Remove intermediate_sql marker if somehow still present
    sql = re.sub(r'intermediate[_\s]?sql[:\s]*', '', sql, flags=re.IGNORECASE)

    # Remove leading/trailing whitespace
    sql = sql.strip()

    # Remove multiple spaces
    sql = re.sub(r'\s+', ' ', sql)

    return sql


def extract_intermediate_sql(response: str) -> str:
    """
    Extract intermediate SQL from LLM response.

    Vanna 2.0 may return intermediate SQL when it needs more context.
    This detects patterns like:
    - Response contains 'intermediate' keyword
    - Response contains SQL but also contains questions or uncertainties
    - Response starts with SELECT but contains reasoning text

    Returns:
        str: The intermediate SQL if detected, empty string otherwise
    """
    if not response or not isinstance(response, str):
        return ""

    response_lower = response.lower()

    # Pattern 1: Explicit intermediate_sql marker
    if 'intermediate_sql' in response_lower or 'intermediate sql' in response_lower:
        # Try to extract SQL after the marker
        sql_start = response.find('SELECT')
        if sql_start == -1:
            sql_start = response.find('select')

        if sql_start >= 0:
            # Extract until we hit a double newline or end of string
            sql_end = response.find('\n\n', sql_start)
            if sql_end > 0:
                intermediate_sql = response[sql_start:sql_end].strip()
            else:
                intermediate_sql = response[sql_start:].strip()

            # Clean up
            intermediate_sql = clean_sql(intermediate_sql)
            if 'SELECT' in intermediate_sql.upper():
                return intermediate_sql

    # Pattern 2: Response contains questions/uncertainties AND SQL
    uncertainty_keywords = ['不确定', '不知道', 'uncertain', 'unclear', '是指', '是不是', '可能', 'might be', 'could be', '需要澄清']
    has_uncertainty = any(keyword in response_lower for keyword in uncertainty_keywords)

    if has_uncertainty and 'select' in response_lower:
        # Extract the SQL part
        sql_start = response.find('SELECT')
        if sql_start == -1:
            sql_start = response.find('select')

        if sql_start >= 0:
            # Look for DISTINCT type queries (common intermediate pattern)
            if 'distinct' in response_lower[sql_start:sql_start+200]:
                sql_end = response.find('\n\n', sql_start)
                if sql_end > 0:
                    intermediate_sql = response[sql_start:sql_end].strip()
                else:
                    # Try to find end of SQL statement
                    sql_end = response.find(';', sql_start)
                    if sql_end > 0:
                        intermediate_sql = response[sql_start:sql_end+1].strip()
                    else:
                        intermediate_sql = response[sql_start:].strip()

                intermediate_sql = clean_sql(intermediate_sql)
                if 'SELECT' in intermediate_sql.upper() and 'DISTINCT' in intermediate_sql.upper():
                    return intermediate_sql

    return ""


def is_clarification_request(response: str) -> bool:
    """
    Check if LLM response is asking for clarification rather than providing SQL.

    Returns:
        bool: True if response appears to be a clarification request
    """
    if not response or not isinstance(response, str):
        return False

    response_lower = response.lower()

    # Keywords indicating clarification needed
    clarification_patterns = [
        '无法确定', '不确定', '需要更多信息', '请明确', '请指定',
        'cannot determine', 'unclear', 'need more information',
        'please clarify', 'please specify', 'could you clarify',
        '请问', '是指', '是不是', '的意思',
        'do you mean', 'what do you mean', 'which',
        '没有找到', 'not found', 'cannot find'
    ]

    has_clarification = any(pattern in response_lower for pattern in clarification_patterns)

    # Also check if response doesn't contain valid SQL
    has_sql = 'select' in response_lower and 'from' in response_lower

    # If it has clarification keywords and no SQL, it's likely a clarification request
    # OR if it has clarification keywords and very short SQL (< 50 chars), might be incomplete
    if has_clarification:
        if not has_sql:
            return True
        else:
            # Extract potential SQL and check if it's complete
            sql_part = response[response_lower.find('select'):]
            if len(sql_part.strip()) < 50:  # Too short to be a real query
                return True

    return False


def clean_sql(sql: str) -> str:
    """
    Clean and normalize SQL string from AI output.
    Removes markdown code blocks and extra whitespace.
    """
    if not sql or not isinstance(sql, str):
        raise ValueError("Invalid SQL output")

    sql = sql.strip()

    # Remove markdown code blocks
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else sql
        if sql.endswith("```"):
            sql = sql.rsplit("\n", 1)[0]

    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql
