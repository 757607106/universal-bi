from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dataset, DataSource, BusinessTerm, User
from app.schemas.dataset import (
    DatasetCreate, DatasetResponse, DatasetUpdateTables,
    BusinessTermCreate, BusinessTermResponse,
    AnalyzeRelationshipsRequest, AnalyzeRelationshipsResponse,
    CreateViewRequest
)
from app.services.vanna_manager import VannaManager

router = APIRouter()

def run_training_task(dataset_id: int, table_names: list[str]):
    """
    Background task wrapper to ensure a separate DB session.
    """
    db = SessionLocal()
    try:
        VannaManager.train_dataset(dataset_id, table_names, db)
    finally:
        db.close()

@router.post("/", response_model=DatasetResponse)
def create_dataset(
    dataset_in: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new dataset.
    应用数据隔离：需要验证 DataSource 的所有权
    """
    # 验证 DataSource 访问权限
    ds_query = db.query(DataSource).filter(DataSource.id == dataset_in.datasource_id)
    ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
    datasource = ds_query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")

    dataset = Dataset(
        name=dataset_in.name,
        datasource_id=dataset_in.datasource_id,
        training_status="pending",
        owner_id=current_user.id  # 自动设置为当前用户
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Auto-generate collection_name based on ID
    dataset.collection_name = f"vec_ds_{dataset.id}"
    db.commit()
    db.refresh(dataset)
    
    return dataset

@router.get("/", response_model=List[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List datasets.
    应用数据隔离：普通用户只能查看自己的数据集和公共资源
    """
    query = db.query(Dataset)
    query = apply_ownership_filter(query, Dataset, current_user)
    datasets = query.offset(skip).limit(limit).all()
    return datasets

@router.put("/{id}/tables", response_model=DatasetResponse)
def update_tables(
    id: int,
    config_in: DatasetUpdateTables,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update selected tables (schema_config) for a dataset.
    应用数据隔离：只能修改自己的数据集
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以修改
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")
        
    dataset.schema_config = config_in.schema_config
    db.commit()
    db.refresh(dataset)
    return dataset

@router.post("/{id}/train")
def train_dataset(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger training for a dataset.
    应用数据隔离：只能训练自己的数据集
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以训练
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot train public resources")
        
    if not dataset.schema_config:
        raise HTTPException(status_code=400, detail="No tables selected for training")
        
    # Check if already training? 
    if dataset.training_status == "training":
        # Optional: Allow restart or block? User didn't specify.
        # We'll allow it but maybe warn? For now just proceed.
        pass

    dataset.training_status = "pending" # Set to pending before background task picks it up (or directly training)
    # Actually VannaManager sets it to 'training'.
    # But to give immediate feedback, maybe we can set it here?
    # VannaManager logic:
    # dataset.training_status = "training"
    # So we don't strictly need to set it here, but it's good UI feedback if we set it to 'pending' or 'queued'.
    # The model default is 'pending'.
    
    background_tasks.add_task(run_training_task, id, dataset.schema_config)
    
    return {"message": "训练已开始"}


# Business Term Management Endpoints
@router.post("/{id}/terms", response_model=BusinessTermResponse)
def add_business_term(
    id: int,
    term_in: BusinessTermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a business term to a dataset and train it in Vanna.
    应用数据隔离：需要验证 Dataset 的所有权
    """
    # Verify dataset exists and user has access
    ds_query = db.query(Dataset).filter(Dataset.id == id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以添加术语
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot add terms to public resources")
    
    # Create business term in database
    business_term = BusinessTerm(
        dataset_id=id,
        term=term_in.term,
        definition=term_in.definition,
        owner_id=current_user.id  # 自动设置为当前用户
    )
    db.add(business_term)
    db.commit()
    db.refresh(business_term)
    
    # Train the term in Vanna
    try:
        VannaManager.train_term(
            dataset_id=id,
            term=term_in.term,
            definition=term_in.definition,
            db_session=db
        )
    except Exception as e:
        # Rollback database if Vanna training fails
        db.delete(business_term)
        db.commit()
        raise HTTPException(status_code=500, detail=f"训练术语失败: {str(e)}")
    
    return business_term


@router.get("/{id}/terms", response_model=List[BusinessTermResponse])
def list_business_terms(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all business terms for a dataset.
    应用数据隔离：需要验证 Dataset 的访问权
    """
    # Verify dataset access
    ds_query = db.query(Dataset).filter(Dataset.id == id)
    ds_query = apply_ownership_filter(ds_query, Dataset, current_user)
    dataset = ds_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 查询术语（也应用隔离）
    term_query = db.query(BusinessTerm).filter(BusinessTerm.dataset_id == id)
    term_query = apply_ownership_filter(term_query, BusinessTerm, current_user)
    terms = term_query.all()
    
    return terms


@router.delete("/terms/{term_id}")
def delete_business_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a business term from database.
    Note: Vanna Legacy API does not provide a direct way to remove specific training data,
    so this only removes from database. The term will remain in the vector store.
    应用数据隔离：只能删除自己的术语
    """
    term_query = db.query(BusinessTerm).filter(BusinessTerm.id == term_id)
    term_query = apply_ownership_filter(term_query, BusinessTerm, current_user)
    term = term_query.first()
    
    if not term:
        raise HTTPException(status_code=404, detail="Business term not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if term.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    db.delete(term)
    db.commit()
    
    return {"message": "术语已删除（注：向量库中的训练数据仍保留）"}


# Modeling Endpoints
@router.post("/analyze", response_model=AnalyzeRelationshipsResponse)
def analyze_relationships(
    request: AnalyzeRelationshipsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze potential relationships between tables using AI.
    应用数据隔离：需要验证 DataSource 的所有权
    """
    # Verify DataSource access
    ds_query = db.query(DataSource).filter(DataSource.id == request.datasource_id)
    ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
    datasource = ds_query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")
    
    if not request.table_names or len(request.table_names) == 0:
        raise HTTPException(status_code=400, detail="At least one table name is required")
    
    # For AI analysis, we need a dataset context. 
    # Create a temporary dataset or use an existing one?
    # For simplicity, we'll create a temporary dataset ID or use datasource_id as hint
    # Actually, VannaManager.analyze_relationships expects a dataset_id for LLM context
    # Let's find or create a dataset for this datasource
    
    # Option 1: Find first dataset for this datasource (if exists)
    dataset_query = db.query(Dataset).filter(Dataset.datasource_id == request.datasource_id)
    dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
    dataset = dataset_query.first()
    
    if not dataset:
        # Option 2: Create a temporary dataset for analysis
        # This is a bit heavy - alternative is to make analyze_relationships work without dataset_id
        # For now, we require an existing dataset
        raise HTTPException(
            status_code=400, 
            detail="No dataset found for this datasource. Please create a dataset first."
        )
    
    try:
        result = VannaManager.analyze_relationships(
            dataset_id=dataset.id,
            table_names=request.table_names,
            db_session=db
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def _deduplicate_sql_columns(sql: str) -> str:
    """
    处理 SQL 中的重复列名问题。
    解析 SELECT 子句，为重复的列名添加表别名前缀。
    
    例如：
    - 输入: SELECT u.user_id, o.user_id, p.product_id FROM ...
    - 输出: SELECT u.user_id AS u_user_id, o.user_id AS o_user_id, p.product_id FROM ...
    """
    import re
    import logging
    logger = logging.getLogger(__name__)
    
    # 提取 SELECT 和 FROM 之间的列定义部分
    select_match = re.match(r'^\s*SELECT\s+(.+?)\s+FROM\s+', sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        logger.warning("Cannot parse SELECT clause, returning original SQL")
        return sql
    
    select_clause = select_match.group(1)
    rest_of_sql = sql[select_match.end() - 5:]  # 保留 FROM 及之后的部分
    
    # 解析各列（考虑逗号分隔）
    # 简单分割，考虑可能的换行
    columns = [col.strip() for col in select_clause.split(',')]
    
    # 统计列名出现次数
    column_names = {}  # {base_name: [(alias, full_column_str), ...]}
    parsed_columns = []  # [(alias, base_name, original_str), ...]
    
    for col in columns:
        if not col:
            continue
        # 解析列名：可能是 alias.column 或 alias.column AS new_name
        # 跳过已有 AS 别名的列
        if ' AS ' in col.upper():
            parsed_columns.append((None, None, col))
            continue
        
        # 匹配 alias.column_name 格式
        col_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)$', col.strip())
        if col_match:
            table_alias = col_match.group(1)
            column_name = col_match.group(2)
            parsed_columns.append((table_alias, column_name, col))
            if column_name not in column_names:
                column_names[column_name] = []
            column_names[column_name].append(table_alias)
        else:
            # 没有表别名或者复杂表达式，保持原样
            parsed_columns.append((None, None, col))
    
    # 找出重复的列名
    duplicate_columns = {name for name, aliases in column_names.items() if len(aliases) > 1}
    
    if not duplicate_columns:
        logger.info("No duplicate columns found")
        return sql
    
    logger.info(f"Found duplicate columns: {duplicate_columns}")
    
    # 重建 SELECT 子句，为重复列添加别名
    new_columns = []
    seen_columns = set()  # 追踪已处理的列，防止完全相同的列重复出现
    
    for table_alias, column_name, original in parsed_columns:
        if table_alias is None or column_name is None:
            # 保持原样
            new_columns.append(original)
        elif column_name in duplicate_columns:
            # 重复列，添加别名 (table_column)
            alias_name = f"{table_alias}_{column_name}"
            # 如果这个完全相同的列已经出现过，跳过
            full_key = f"{table_alias}.{column_name}"
            if full_key in seen_columns:
                continue
            seen_columns.add(full_key)
            new_columns.append(f"{original} AS {alias_name}")
        else:
            # 非重复列，检查是否已存在
            full_key = f"{table_alias}.{column_name}"
            if full_key in seen_columns:
                continue
            seen_columns.add(full_key)
            new_columns.append(original)
    
    # 重建 SQL
    new_select_clause = ',\n  '.join(new_columns)
    new_sql = f"SELECT \n  {new_select_clause}\nFROM {rest_of_sql[5:]}"  # 去掉前面的 FROM
    
    logger.info(f"Deduplicated SQL: {new_sql[:300]}...")
    return new_sql


@router.post("/create_view")
def create_view(
    request: CreateViewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or replace a database view based on the provided SQL.
    This materializes the wide table in the database for better query performance.
    应用数据隔离：需要验证 DataSource 的所有权
    """
    # Verify DataSource access
    ds_query = db.query(DataSource).filter(DataSource.id == request.datasource_id)
    ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
    datasource = ds_query.first()
    
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以创建视图
    if datasource.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot create views on public datasources")
    
    # Validate view_name (prevent SQL injection)
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', request.view_name):
        raise HTTPException(status_code=400, detail="Invalid view name. Use only alphanumeric and underscore.")
    
    # Validate SQL (basic check - should be SELECT)
    if not request.sql.strip().upper().startswith('SELECT'):
        raise HTTPException(status_code=400, detail="SQL must be a SELECT query")
    
    try:
        from app.services.db_inspector import DBInspector
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Creating view: {request.view_name}")
        logger.info(f"Datasource ID: {request.datasource_id}")
        logger.info(f"Original SQL: {request.sql[:200]}...")
        
        # 自动处理重复列名问题
        processed_sql = _deduplicate_sql_columns(request.sql)
        logger.info(f"Processed SQL: {processed_sql[:200]}...")
        
        engine = DBInspector.get_engine(datasource)
        
        # Create or replace view
        # Note: Syntax varies by database type
        if datasource.type == 'postgresql':
            create_view_sql = f"CREATE OR REPLACE VIEW {request.view_name} AS {processed_sql}"
        elif datasource.type == 'mysql':
            # MySQL requires dropping the view first if it exists
            drop_view_sql = f"DROP VIEW IF EXISTS {request.view_name}"
            create_view_sql = f"CREATE VIEW {request.view_name} AS {processed_sql}"
            
            logger.info(f"Executing DROP VIEW: {drop_view_sql}")
            with engine.connect() as conn:
                conn.execute(text(drop_view_sql))
                conn.commit()
        else:
            # Default to CREATE OR REPLACE
            create_view_sql = f"CREATE OR REPLACE VIEW {request.view_name} AS {processed_sql}"
        
        logger.info(f"Executing CREATE VIEW: {create_view_sql[:200]}...")
        
        # Execute create view
        with engine.connect() as conn:
            conn.execute(text(create_view_sql))
            conn.commit()
        
        logger.info(f"View {request.view_name} created successfully")
        
        return {
            "message": f"视图 {request.view_name} 创建成功",
            "view_name": request.view_name
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create view: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建视图失败: {str(e)}")
