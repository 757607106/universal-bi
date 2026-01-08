from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dataset, DataSource, BusinessTerm, User, TrainingLog
from app.schemas.dataset import (
    DatasetCreate, DatasetResponse, DatasetUpdateTables,
    BusinessTermCreate, BusinessTermResponse,
    AnalyzeRelationshipsRequest, AnalyzeRelationshipsResponse,
    CreateViewRequest, TrainingLogResponse, TrainingDataResponse,
    TrainQARequest, TrainDocRequest
)
from app.services.vanna import (
    VannaInstanceManager,
    VannaTrainingService,
    VannaCacheService,
    VannaTrainingDataService,
    VannaAnalystService
)

router = APIRouter()

def run_training_task(dataset_id: int, table_names: list[str]):
    """
    Background task wrapper to ensure a separate DB session.
    """
    db = SessionLocal()
    try:
        VannaTrainingService.train_dataset(dataset_id, table_names, db)
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
        status="pending",
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

@router.get("/{id}", response_model=DatasetResponse)
def get_dataset(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single dataset by ID.
    应用数据隔离：只能查看自己的数据集和公共资源
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    return dataset

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
    if dataset.status == "training":
        # Optional: Allow restart or block? User didn't specify.
        # We'll allow it but maybe warn? For now just proceed.
        pass

    dataset.status = "pending" # Set to pending before background task picks it up (or directly training)
    # Actually VannaManager sets it to 'training'.
    # But to give immediate feedback, maybe we can set it here?
    # VannaManager logic:
    # dataset.status = "training"
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
        VannaTrainingService.train_term(
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


# ===== QA Training Endpoints =====

@router.post("/{id}/training/qa")
def train_qa_pair(
    id: int,
    qa_data: TrainQARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    训练一个 QA 对（问题-SQL 对）
    这将帮助 AI 学习如何将特定问题转化为 SQL 查询
    
    Args:
        id: 数据集 ID
        qa_data: 包含 question 和 sql 的请求体
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以添加训练数据
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot add training data to public resources")
    
    try:
        VannaTrainingService.train_qa(
            dataset_id=id,
            question=qa_data.question,
            sql=qa_data.sql,
            db_session=db
        )
        return {
            "message": "QA对训练成功",
            "question": qa_data.question,
            "sql": qa_data.sql
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA对训练失败: {str(e)}")


@router.post("/{id}/training/doc")
def train_documentation(
    id: int,
    doc_data: TrainDocRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    训练一个文档（业务规则、描述等）
    这将帮助 AI 理解业务上下文和规则
    
    Args:
        id: 数据集 ID
        doc_data: 包含 content 的请求体
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以添加训练数据
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot add training data to public resources")
    
    try:
        # 获取 Legacy Vanna 实例并训练文档
        vn = VannaInstanceManager.get_legacy_vanna(id)
        vn.train(documentation=doc_data.content)

        # 注意：缓存清理需要在异步上下文中处理
        # VannaCacheService.clear_cache(id) 是异步方法

        return {
            "message": "文档训练成功",
            "content": doc_data.content[:100] + "..." if len(doc_data.content) > 100 else doc_data.content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档训练失败: {str(e)}")


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
        result = VannaAnalystService.analyze_relationships(
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


def _train_relationships_from_edges(dataset_id: int, edges: list, db_session: Session):
    """
    从 VueFlow edges 解析表关系并训练到 Vanna。

    Args:
        dataset_id: 数据集 ID
        edges: VueFlow edges 数据列表
        db_session: 数据库会话

    VueFlow Edge 结构示例：
    {
        "id": "edge-1",
        "source": "node-users",  # 节点 ID
        "target": "node-orders",
        "sourceHandle": "id",    # 字段名
        "targetHandle": "user_id",
        "data": {
            "sourceTable": "users",    # 表名
            "targetTable": "orders",
            "sourceField": "id",
            "targetField": "user_id"
        }
    }

    Returns:
        dict: {
            "success": bool,
            "trained_count": int,
            "skipped_count": int,
            "validation_errors": list[str]
        }
    """
    import logging
    from app.services.db_inspector import DBInspector

    logger = logging.getLogger(__name__)

    result = {
        "success": True,
        "trained_count": 0,
        "skipped_count": 0,
        "validation_errors": []
    }

    if not edges or len(edges) == 0:
        logger.info(f"No edges to train for dataset {dataset_id}")
        return result

    # 获取 dataset 和关联的 datasource 用于验证
    dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        result["success"] = False
        result["validation_errors"].append(f"Dataset {dataset_id} not found")
        return result

    datasource = db_session.query(DataSource).filter(DataSource.id == dataset.datasource_id).first()
    if not datasource:
        result["success"] = False
        result["validation_errors"].append(f"DataSource not found for dataset {dataset_id}")
        return result

    # 缓存已验证的表和列信息，避免重复查询
    validated_tables = {}  # table_name -> set(column_names)

    def validate_table_column(table_name: str, column_name: str) -> tuple[bool, str]:
        """验证表和列是否存在，返回 (is_valid, error_message)"""
        if table_name not in validated_tables:
            try:
                validation = DBInspector.validate_table_and_columns(datasource, table_name, [])
                if not validation["table_exists"]:
                    return False, f"表 '{table_name}' 在数据库中不存在"
                # 获取所有列名并缓存
                columns = DBInspector.get_column_names(datasource, table_name)
                validated_tables[table_name] = set(columns)
            except Exception as e:
                return False, f"验证表 '{table_name}' 时出错: {str(e)}"

        if column_name not in validated_tables[table_name]:
            return False, f"列 '{column_name}' 在表 '{table_name}' 中不存在"

        return True, ""

    relationships = []

    for edge in edges:
        try:
            # 方法1：从 data 中获取表名和字段名（优先）
            if 'data' in edge and edge['data']:
                data = edge['data']
                source_table = data.get('sourceTable')
                target_table = data.get('targetTable')
                source_field = data.get('sourceField')
                target_field = data.get('targetField')
            else:
                # 方法2：从 source/target 和 handle 中解析
                # 假设节点 ID 格式为 "node-{table_name}"
                source_node_id = edge.get('source', '')
                target_node_id = edge.get('target', '')

                # 提取表名（移除 "node-" 前缀）
                source_table = source_node_id.replace('node-', '') if source_node_id.startswith('node-') else source_node_id
                target_table = target_node_id.replace('node-', '') if target_node_id.startswith('node-') else target_node_id

                # Handle 即为字段名
                source_field = edge.get('sourceHandle', '')
                target_field = edge.get('targetHandle', '')

            # 验证必要字段
            if not all([source_table, target_table, source_field, target_field]):
                error_msg = f"Edge {edge.get('id', 'unknown')}: 缺少必要的表名或字段名"
                logger.warning(error_msg)
                result["validation_errors"].append(error_msg)
                result["skipped_count"] += 1
                continue

            # P0: 验证表和字段是否存在于数据库中
            is_valid, error = validate_table_column(source_table, source_field)
            if not is_valid:
                error_msg = f"Edge {edge.get('id', 'unknown')}: {error}"
                logger.warning(error_msg)
                result["validation_errors"].append(error_msg)
                result["skipped_count"] += 1
                continue

            is_valid, error = validate_table_column(target_table, target_field)
            if not is_valid:
                error_msg = f"Edge {edge.get('id', 'unknown')}: {error}"
                logger.warning(error_msg)
                result["validation_errors"].append(error_msg)
                result["skipped_count"] += 1
                continue

            # 推断关系类型（基于字段命名约定）
            is_fk_pattern = target_field.endswith('_id') or target_field == 'id'
            cardinality = "Many-to-One" if is_fk_pattern else "One-to-One (inferred)"

            # 生成增强版关系描述（单向，包含 SQL 示例和业务含义）
            enhanced_desc = f"""## Table Relationship: {source_table} → {target_table}

**Join Condition**: `{source_table}`.`{source_field}` = `{target_table}`.`{target_field}`

**Relationship Type**: {cardinality}
- The `{source_field}` column in `{source_table}` references `{target_field}` in `{target_table}`
- When querying {source_table} data with related {target_table} information, use LEFT JOIN

**Recommended SQL Pattern**:
```sql
SELECT s.*, t.*
FROM {source_table} s
LEFT JOIN {target_table} t ON s.{source_field} = t.{target_field}
```

**Business Context**: Each record in `{source_table}` is associated with one record in `{target_table}` through the `{source_field}` field."""

            relationships.append(enhanced_desc)

            logger.debug(f"Validated relationship: {source_table}.{source_field} <-> {target_table}.{target_field}")

        except Exception as e:
            error_msg = f"Edge {edge.get('id', 'unknown')}: 解析失败 - {str(e)}"
            logger.warning(error_msg)
            result["validation_errors"].append(error_msg)
            result["skipped_count"] += 1
            continue

    if len(relationships) > 0:
        logger.info(f"Training {len(relationships)} validated relationship descriptions for dataset {dataset_id}")
        VannaTrainingService.train_relationships(dataset_id, relationships, db_session)
        result["trained_count"] = len(relationships)
    else:
        logger.info(f"No valid relationships extracted from {len(edges)} edges")

    result["success"] = len(result["validation_errors"]) == 0
    return result


def _analyze_sql_performance(engine, sql: str, db_type: str) -> dict:
    """
    分析 SQL 性能，返回警告信息。

    Args:
        engine: SQLAlchemy 引擎
        sql: 要分析的 SQL 语句
        db_type: 数据库类型 ('mysql', 'postgresql')

    Returns:
        dict: {
            "warnings": list[str],  # 警告信息列表
            "estimated_rows": int,  # 预估行数
            "has_full_scan": bool   # 是否有全表扫描
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    result = {
        "warnings": [],
        "estimated_rows": 0,
        "has_full_scan": False
    }

    try:
        with engine.connect() as conn:
            if db_type == 'mysql':
                # MySQL EXPLAIN
                explain_result = conn.execute(text(f"EXPLAIN {sql}"))
                rows = explain_result.fetchall()

                for row in rows:
                    # MySQL EXPLAIN 列: id, select_type, table, type, possible_keys, key, key_len, ref, rows, Extra
                    row_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(explain_result.keys(), row))

                    # 检测全表扫描
                    scan_type = row_dict.get('type', '')
                    if scan_type == 'ALL':
                        result["has_full_scan"] = True
                        table_name = row_dict.get('table', 'unknown')
                        result["warnings"].append(f"表 {table_name} 将执行全表扫描")

                    # 累计预估行数
                    rows_count = row_dict.get('rows', 0)
                    if rows_count:
                        result["estimated_rows"] += int(rows_count)

                    # 检测临时表使用
                    extra = row_dict.get('Extra', '') or ''
                    if 'Using temporary' in extra:
                        result["warnings"].append("查询将使用临时表")
                    if 'Using filesort' in extra:
                        result["warnings"].append("查询将使用文件排序")

            elif db_type == 'postgresql':
                # PostgreSQL EXPLAIN (不使用 ANALYZE 避免实际执行)
                explain_result = conn.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
                explain_json = explain_result.fetchone()[0]

                if explain_json and len(explain_json) > 0:
                    plan = explain_json[0].get('Plan', {})

                    # 提取预估行数
                    result["estimated_rows"] = int(plan.get('Plan Rows', 0))

                    # 检测全表扫描
                    node_type = plan.get('Node Type', '')
                    if node_type == 'Seq Scan':
                        result["has_full_scan"] = True
                        relation = plan.get('Relation Name', 'unknown')
                        result["warnings"].append(f"表 {relation} 将执行顺序扫描 (Seq Scan)")

                    # 递归检查子计划
                    def check_plans(node):
                        if isinstance(node, dict):
                            if node.get('Node Type') == 'Seq Scan':
                                relation = node.get('Relation Name', 'unknown')
                                if f"表 {relation} 将执行顺序扫描" not in str(result["warnings"]):
                                    result["warnings"].append(f"表 {relation} 将执行顺序扫描 (Seq Scan)")
                                    result["has_full_scan"] = True
                            for child in node.get('Plans', []):
                                check_plans(child)

                    check_plans(plan)

        # 添加行数警告
        if result["estimated_rows"] > 100000:
            result["warnings"].append(f"预估结果行数较大 ({result['estimated_rows']:,} 行)，查询可能较慢")
        elif result["estimated_rows"] > 1000000:
            result["warnings"].append(f"预估结果行数非常大 ({result['estimated_rows']:,} 行)，强烈建议添加索引")

    except Exception as e:
        logger.warning(f"SQL 性能分析失败: {e}")
        # 分析失败不阻止视图创建，只记录警告
        result["warnings"].append(f"性能分析跳过: {str(e)}")

    return result


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

        # 性能预检：分析 SQL 执行计划
        perf_analysis = _analyze_sql_performance(engine, processed_sql, datasource.type)
        if perf_analysis["warnings"]:
            logger.warning(f"SQL 性能警告: {perf_analysis['warnings']}")

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

        # 构建响应，包含性能警告信息
        response = {
            "message": f"视图 {request.view_name} 创建成功",
            "view_name": request.view_name,
            "performance": {
                "warnings": perf_analysis.get("warnings", []),
                "estimated_rows": perf_analysis.get("estimated_rows", 0),
                "has_full_scan": perf_analysis.get("has_full_scan", False)
            }
        }

        # 如果有警告，在消息中提示
        if perf_analysis.get("warnings"):
            response["message"] += "（有性能警告，请查看详情）"

        return response
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create view: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建视图失败: {str(e)}")


# ===== Training Progress Management Endpoints =====

@router.get("/{id}/training/progress")
def get_training_progress(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取训练进度
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 获取最新的日志作为 current_step
    latest_log = db.query(TrainingLog).filter(
        TrainingLog.dataset_id == id
    ).order_by(TrainingLog.created_at.desc()).first()
    
    current_step = latest_log.content if latest_log else "等待开始..."
    
    return {
        "status": dataset.status,
        "process_rate": dataset.process_rate,
        "error_msg": dataset.error_msg,
        "current_step": current_step
    }


@router.get("/{id}/training/logs", response_model=List[TrainingLogResponse])
def get_training_logs(
    id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取训练日志
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 查询日志
    logs = db.query(TrainingLog).filter(
        TrainingLog.dataset_id == id
    ).order_by(TrainingLog.created_at.desc()).limit(limit).all()
    
    return logs


@router.get("/{id}/training/data", response_model=TrainingDataResponse)
def get_training_data(
    id: int,
    page: int = 1,
    page_size: int = 20,
    type_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取已训练的数据（QA对、DDL、文档）
    应用数据隔离：需要验证 Dataset 的访问权
    
    Args:
        id: 数据集 ID
        page: 页码（从1开始）
        page_size: 每页数量（默认20）
        type_filter: 类型筛选，可选值: 'ddl', 'sql', 'documentation'
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        # 调用 VannaTrainingDataService 获取训练数据
        result = VannaTrainingDataService.get_training_data(id, page, page_size, type_filter)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取训练数据失败: {str(e)}")


@router.post("/{id}/training/pause")
def pause_training(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    暂停训练
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    if dataset.status != "training":
        raise HTTPException(status_code=400, detail="Dataset is not training")
    
    # 额外检查：公共资源只有超级管理员可以暂停
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot pause training for public resources")
    
    dataset.status = "paused"
    db.commit()
    
    return {"message": "训练暂停请求已发送"}


@router.delete("/{id}/training/data/{training_data_id}")
def remove_single_training_data(
    id: int,
    training_data_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除单条训练数据（DDL、文档或 QA 对）

    Args:
        id: 数据集 ID
        training_data_id: 训练数据 ID
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")

    # 额外检查：公共资源只有超级管理员可以删除
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete training data from public resources")

    success = VannaTrainingDataService.remove_training_data(id, training_data_id)

    if success:
        return {"message": "训练数据已删除", "id": training_data_id}
    else:
        raise HTTPException(status_code=404, detail="训练数据不存在或格式不正确")


@router.delete("/{id}/training")
def delete_training_data(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除训练数据（清理 Collection）
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete training data for public resources")
    
    # 调用 VannaInstanceManager 删除 collection
    success = VannaInstanceManager.delete_collection(id)

    if success:
        return {"message": "训练数据已清理"}
    else:
        raise HTTPException(status_code=500, detail="清理训练数据失败")


@router.delete("/{id}")
def delete_dataset(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除数据集（包含级联删除训练数据、业务术语、训练日志等）
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以删除
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    # 1. 删除 Vanna Collection (训练数据)
    try:
        VannaInstanceManager.delete_collection(id)
    except Exception as e:
        # 记录日志但继续删除
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to delete collection for dataset {id}: {e}")
    
    # 2. 删除数据库记录（级联删除会自动删除 business_terms 和 training_logs）
    db.delete(dataset)
    db.commit()
    
    return {"message": "数据集已删除"}


@router.put("/{id}/modeling-config")
def update_modeling_config(
    id: int,
    config: dict,
    train_relationships: bool = False,  # 新增参数：是否立即训练关系
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新数据集的建模配置（保存画布数据）。
    当 train_relationships=True 时，会解析 edges 并训练表关系到 Vanna。
    
    Args:
        id: 数据集 ID
        config: 建模配置（包含 nodes 和 edges）
        train_relationships: 是否立即训练关系（默认 False）
        db: 数据库会话
        current_user: 当前用户
    """
    import logging
    logger = logging.getLogger(__name__)
    
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 额外检查：公共资源只有超级管理员可以修改
    if dataset.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot modify public resources")
    
    # 检测 edges 是否发生变化
    old_edges = dataset.modeling_config.get('edges', []) if dataset.modeling_config else []
    new_edges = config.get('edges', [])
    
    edges_changed = False
    if len(old_edges) != len(new_edges):
        edges_changed = True
    else:
        # 比较 edge IDs
        old_edge_ids = {edge.get('id') for edge in old_edges if edge.get('id')}
        new_edge_ids = {edge.get('id') for edge in new_edges if edge.get('id')}
        edges_changed = old_edge_ids != new_edge_ids
    
    logger.info(f"Updating modeling config for dataset {id}, edges_changed={edges_changed}, train_relationships={train_relationships}")
    
    # 保存配置
    dataset.modeling_config = config
    db.commit()
    db.refresh(dataset)
    
    # 如果连线发生变化且用户要求训练
    if train_relationships and new_edges and len(new_edges) > 0:
        try:
            logger.info(f"Training relationships from {len(new_edges)} edges for dataset {id}")
            train_result = _train_relationships_from_edges(id, new_edges, db)

            # 根据验证结果构建响应
            if train_result["success"]:
                return {
                    "message": f"建模配置已保存，{train_result['trained_count']} 个表关系已训练",
                    "modeling_config": dataset.modeling_config,
                    "relationships_trained": True,
                    "trained_count": train_result["trained_count"],
                    "edges_count": len(new_edges)
                }
            elif train_result["trained_count"] > 0:
                # 部分成功
                return {
                    "message": f"建模配置已保存，{train_result['trained_count']} 个表关系已训练，{train_result['skipped_count']} 个跳过",
                    "modeling_config": dataset.modeling_config,
                    "relationships_trained": True,
                    "trained_count": train_result["trained_count"],
                    "skipped_count": train_result["skipped_count"],
                    "validation_errors": train_result["validation_errors"],
                    "edges_count": len(new_edges)
                }
            else:
                # 全部验证失败
                return {
                    "message": "建模配置已保存，但所有表关系验证失败",
                    "modeling_config": dataset.modeling_config,
                    "relationships_trained": False,
                    "skipped_count": train_result["skipped_count"],
                    "validation_errors": train_result["validation_errors"]
                }
        except Exception as e:
            logger.error(f"Failed to train relationships: {e}", exc_info=True)
            # 训练失败不影响保存逻辑
            return {
                "message": "建模配置已保存，但表关系训练失败",
                "modeling_config": dataset.modeling_config,
                "relationships_trained": False,
                "error": str(e)
            }
    
    return {
        "message": "建模配置已保存",
        "modeling_config": dataset.modeling_config,
        "relationships_trained": False
    }
