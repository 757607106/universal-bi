from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import time

from app.db.session import get_db, SessionLocal
from app.api.deps import get_current_user, apply_ownership_filter
from app.models.metadata import Dataset, DataSource, BusinessTerm, User, TrainingLog, ComputedMetric
from app.schemas.dataset import (
    DatasetCreate, DatasetResponse, DatasetUpdateTables,
    BusinessTermCreate, BusinessTermResponse,
    AnalyzeRelationshipsRequest, AnalyzeRelationshipsResponse,
    EdgeResponse, NodeResponse, FieldResponse,
    CreateViewRequest, TrainingLogResponse, TrainingDataResponse,
    TrainQARequest, TrainDocRequest, SuggestedQuestions
)
from app.services.vanna import (
    VannaInstanceManager,
    VannaTrainingService,
    VannaCacheService,
    VannaTrainingDataService,
    VannaAnalystService
)
from app.services.vanna.facade import VannaManager
from app.services.vanna.relationship_analyzer import RelationshipAnalyzer
from app.services.duckdb_service import DuckDBService

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

@router.get("/{id}/tables")
def get_dataset_tables(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tables and their schemas for a dataset.
    支持 DuckDB 和传统数据源。
    """
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    try:
        # 检查是否为 DuckDB 数据集
        if dataset.duckdb_path:
            # 从 DuckDB 获取表信息
            from app.core.logger import get_logger
            logger = get_logger(__name__)
            
            logger.info(f"Getting tables from DuckDB for dataset {id}, duckdb_path: {dataset.duckdb_path}")
            logger.info(f"Dataset schema_config: {dataset.schema_config}")
            
            # 获取数据集中的所有表名
            table_names = dataset.schema_config or []
            
            if not table_names:
                logger.warning(f"Dataset {id} has no tables in schema_config")
                return []
            
            tables_info = []
            for table_name in table_names:
                try:
                    logger.info(f"Getting schema for table: {table_name}")
                    schema = DuckDBService.get_table_schema(dataset.duckdb_path, table_name)
                    logger.info(f"Schema for {table_name}: {schema}")
                    columns = [
                        {
                            'name': col['name'],
                            'type': col['type'],
                            'nullable': col.get('nullable', True),
                            'default': None
                        }
                        for col in schema
                    ]
                    tables_info.append({
                        'name': table_name,
                        'columns': columns
                    })
                    logger.info(f"Successfully loaded table {table_name} with {len(columns)} columns")
                except Exception as e:
                    logger.error(f"Failed to get schema for table {table_name}: {e}", exc_info=True)
                    tables_info.append({
                        'name': table_name,
                        'columns': []
                    })
            
            logger.info(f"Returning {len(tables_info)} tables from DuckDB: {[t['name'] for t in tables_info]}")
            return tables_info
        else:
            # 传统数据源：从 datasource 获取表信息
            if not dataset.datasource:
                raise HTTPException(status_code=400, detail="Dataset has no associated datasource")
            
            from app.services.db_inspector import DBInspector
            from sqlalchemy import inspect as sa_inspect
            
            table_names = dataset.schema_config or []
            if not table_names:
                return []
            
            engine = DBInspector.get_engine(dataset.datasource)
            inspector = sa_inspect(engine)
            
            tables_info = []
            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    column_info = [
                        {
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col.get('nullable', True),
                            'default': str(col.get('default')) if col.get('default') is not None else None
                        }
                        for col in columns
                    ]
                    tables_info.append({
                        'name': table_name,
                        'columns': column_info
                    })
                except Exception as e:
                    logger.warning(f"Failed to get columns for table {table_name}: {e}")
                    tables_info.append({
                        'name': table_name,
                        'columns': []
                    })
            
            return tables_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")

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
        # 清理该数据集的缓存，避免返回过时的SQL
        VannaManager.clear_cache(id)
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
        # 清理该数据集的缓存，避免返回过时的SQL
        VannaManager.clear_cache(id)
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

        # 清理该数据集的缓存，避免返回过时的SQL
        VannaManager.clear_cache(id)

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
    支持两种数据源：
    1. 传统数据源（MySQL/PostgreSQL）- 使用 VannaAnalystService
    2. DuckDB 数据源 - 使用 RelationshipAnalyzer
    
    判断逻辑：
    - 优先查找包含指定表的 DuckDB 数据集（duckdb_path 不为空）
    - 如果没有 DuckDB 数据集，再使用传统数据源分析
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not request.table_names or len(request.table_names) == 0:
        raise HTTPException(status_code=400, detail="At least one table name is required")
    
    # 🔧 修复：优先查找 DuckDB 数据集（多文件上传场景）
    # 查找包含这些表的 DuckDB 数据集
    duckdb_datasets = db.query(Dataset).filter(
        Dataset.duckdb_path.isnot(None),
        Dataset.owner_id == current_user.id
    ).all()
    
    # 找到包含所有指定表的 DuckDB 数据集
    target_duckdb_dataset = None
    for dataset in duckdb_datasets:
        if dataset.schema_config and all(
            table in dataset.schema_config for table in request.table_names
        ):
            target_duckdb_dataset = dataset
            break
    
    # 方案1：如果找到 DuckDB 数据集，使用 RelationshipAnalyzer
    if target_duckdb_dataset:
        try:
            logger.info(
                f"Using RelationshipAnalyzer for DuckDB dataset {target_duckdb_dataset.id}, "
                f"tables: {request.table_names}"
            )
            
            # 使用 RelationshipAnalyzer 分析
            relationships = RelationshipAnalyzer.analyze_relationships(
                dataset_id=target_duckdb_dataset.id,
                db_path=target_duckdb_dataset.duckdb_path,
                table_names=request.table_names
            )
            
            # 转换为 API 响应格式
            edges = [
                EdgeResponse(
                    source=rel['source'],
                    target=rel['target'],
                    source_col=rel['source_col'],
                    target_col=rel['target_col'],
                    type=rel.get('type', 'left'),
                    confidence=f"{rel.get('confidence', 'medium')} ({rel.get('data_overlap', 0):.1f}% overlap)"
                )
                for rel in relationships
            ]
            
            # 获取节点信息（表结构）
            nodes = []
            for table_name in request.table_names:
                schema = DuckDBService.get_table_schema(target_duckdb_dataset.duckdb_path, table_name)
                fields = [
                    FieldResponse(
                        name=col['name'],
                        type=col['type'],
                        nullable=col.get('nullable', True)
                    )
                    for col in schema
                ]
                nodes.append(NodeResponse(table_name=table_name, fields=fields))
            
            return AnalyzeRelationshipsResponse(edges=edges, nodes=nodes)
        
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"DuckDB relationship analysis failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
    
    # 方案2：没有 DuckDB 数据集，使用传统数据源分析
    if request.datasource_id:
        # Verify DataSource access
        ds_query = db.query(DataSource).filter(DataSource.id == request.datasource_id)
        ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
        datasource = ds_query.first()
        
        if not datasource:
            raise HTTPException(status_code=404, detail="DataSource not found or access denied")
        
        # Find dataset for this datasource
        dataset_query = db.query(Dataset).filter(Dataset.datasource_id == request.datasource_id)
        dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
        dataset = dataset_query.first()
        
        if not dataset:
            raise HTTPException(
                status_code=400, 
                detail="No dataset found for this datasource. Please create a dataset first."
            )
        
        try:
            logger.info(
                f"Using RelationshipAnalyzer for traditional datasource, "
                f"dataset_id: {dataset.id}, datasource_id: {request.datasource_id}"
            )
            
            from app.services.db_inspector import DBInspector
            engine = DBInspector.get_engine(datasource)
            
            # 使用 RelationshipAnalyzer 分析（复用相同的智能分析逻辑）
            relationships = RelationshipAnalyzer.analyze_relationships(
                dataset_id=dataset.id,
                table_names=request.table_names,
                engine=engine
            )
            
            # 转换为 API 响应格式 (edges)
            edges = [
                EdgeResponse(
                    source=rel['source'],
                    target=rel['target'],
                    source_col=rel['source_col'],
                    target_col=rel['target_col'],
                    type=rel.get('type', 'left'),
                    confidence=f"{rel.get('confidence', 'medium')} ({rel.get('data_overlap', 0):.1f}% overlap)"
                )
                for rel in relationships
            ]
            
            # 获取节点信息（表结构）
            from sqlalchemy import inspect as sa_inspect
            inspector = sa_inspect(engine)
            nodes = []
            
            for table_name in request.table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    fields = [
                        FieldResponse(
                            name=col['name'],
                            type=str(col['type']),
                            nullable=col.get('nullable', True)
                        )
                        for col in columns
                    ]
                    nodes.append(NodeResponse(table_name=table_name, fields=fields))
                except Exception as e:
                    logger.warning(f"Failed to get columns for {table_name}: {e}")
                    nodes.append(NodeResponse(table_name=table_name, fields=[]))

            return AnalyzeRelationshipsResponse(edges=edges, nodes=nodes)
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
    
    # 没有找到任何可用的数据集
    raise HTTPException(
        status_code=404,
        detail="未找到包含指定表的数据集，请先上传数据或连接数据源"
    )


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
    支持传统数据源和DuckDB数据集两种模式：
    - 传统模式：需要 datasource_id
    - DuckDB模式：需要 dataset_id
    """
    # #region agent log
    import json; open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').write(json.dumps({"location": "dataset.py:create_view:entry", "message": "create_view called", "data": {"datasource_id": request.datasource_id, "dataset_id": request.dataset_id, "view_name": request.view_name, "user_id": current_user.id, "is_superuser": current_user.is_superuser}, "timestamp": __import__('time').time() * 1000, "sessionId": "debug-session", "hypothesisId": "H1,H3"}) + '\n'); open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').close()
    # #endregion
    
    datasource = None
    dataset = None
    
    # 模式1: DuckDB数据集模式
    if request.dataset_id:
        # #region agent log
        import json; open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').write(json.dumps({"location": "dataset.py:create_view:duckdb_mode", "message": "using DuckDB mode", "data": {"dataset_id": request.dataset_id}, "timestamp": __import__('time').time() * 1000, "sessionId": "debug-session", "hypothesisId": "H1"}) + '\n'); open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').close()
        # #endregion
        
        # 查找并验证Dataset权限
        dataset_query = db.query(Dataset).filter(Dataset.id == request.dataset_id)
        dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
        dataset = dataset_query.first()
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found or access denied")
        
        # 【修复】检查是否为DuckDB数据集，如果不是且有datasource_id，则降级到传统模式
        if not dataset.duckdb_path:
            if dataset.datasource_id:
                # 降级到传统数据源模式
                request.datasource_id = dataset.datasource_id
                dataset = None  # 清空dataset，使用datasource模式
            else:
                raise HTTPException(status_code=400, detail="此数据集既不是DuckDB数据集，也没有关联数据源")
    
    # 模式2: 传统数据源模式
    if request.datasource_id and not dataset:
        # #region agent log
        import json; open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').write(json.dumps({"location": "dataset.py:create_view:datasource_mode", "message": "using DataSource mode", "data": {"datasource_id": request.datasource_id}, "timestamp": __import__('time').time() * 1000, "sessionId": "debug-session", "hypothesisId": "H1"}) + '\n'); open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').close()
        # #endregion
        
        # 查找并验证DataSource权限
        ds_query = db.query(DataSource).filter(DataSource.id == request.datasource_id)
        ds_query = apply_ownership_filter(ds_query, DataSource, current_user)
        datasource = ds_query.first()
        
        if not datasource:
            raise HTTPException(status_code=404, detail="DataSource not found or access denied")
        
        # 额外检查：公共资源只有超级管理员可以创建视图
        if datasource.owner_id is None and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Cannot create views on public datasources")
    
    else:
        raise HTTPException(status_code=400, detail="必须提供 datasource_id 或 dataset_id")
    
    # Validate view_name (prevent SQL injection)
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', request.view_name):
        raise HTTPException(status_code=400, detail="Invalid view name. Use only alphanumeric and underscore.")
    
    # Validate SQL (增强安全检查)
    sql_upper = request.sql.strip().upper()
    
    # 1. 检查必须以 SELECT 开头
    if not sql_upper.startswith('SELECT'):
        raise HTTPException(status_code=400, detail="SQL must be a SELECT query")
    
    # 2. 检查危险关键字
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 
        'ALTER', 'CREATE TABLE', 'CREATE INDEX', 'EXEC', 
        'EXECUTE', 'GRANT', 'REVOKE'
    ]
    
    for keyword in DANGEROUS_KEYWORDS:
        # 使用单词边界检查，避免误判（如 "SELECTED" 不应匹配 "SELECT"）
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            raise HTTPException(
                status_code=400, 
                detail=f"SQL 不允许包含危险语句: {keyword}"
            )
    
    try:
        from app.services.db_inspector import DBInspector
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Creating view: {request.view_name}")

        # 自动处理重复列名问题
        processed_sql = _deduplicate_sql_columns(request.sql)
        logger.info(f"Processed SQL: {processed_sql[:200]}...")

        # 根据模式选择不同的执行引擎
        if dataset and dataset.duckdb_path:
            # DuckDB模式
            logger.info(f"Using DuckDB at: {dataset.duckdb_path}")
            
            # #region agent log
            import json; open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').write(json.dumps({"location": "dataset.py:create_view:duckdb_execution", "message": "creating view in DuckDB", "data": {"duckdb_path": dataset.duckdb_path}, "timestamp": __import__('time').time() * 1000, "sessionId": "debug-session", "hypothesisId": "H1"}) + '\n'); open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').close()
            # #endregion
            
            import duckdb
            
            # DuckDB 使用 CREATE OR REPLACE VIEW 语法
            create_view_sql = f"CREATE OR REPLACE VIEW {request.view_name} AS {processed_sql}"
            
            logger.info(f"Executing DuckDB CREATE VIEW: {create_view_sql[:200]}...")
            
            # 执行创建视图（直接使用duckdb连接）
            conn = duckdb.connect(dataset.duckdb_path)
            try:
                conn.execute(create_view_sql)
                conn.commit()
                
                # #region agent log
                import json; open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').write(json.dumps({"location": "dataset.py:create_view:duckdb_success", "message": "DuckDB view created successfully", "data": {"view_name": request.view_name}, "timestamp": __import__('time').time() * 1000, "sessionId": "debug-session", "hypothesisId": "H1"}) + '\n'); open('/Users/pusonglin/PycharmProjects/universal-bi/.cursor/debug.log', 'a').close()
                # #endregion
            finally:
                conn.close()
            
            logger.info(f"DuckDB view {request.view_name} created successfully")
            
            # DuckDB模式的响应（暂不分析性能）
            return {
                "message": f"视图 {request.view_name} 创建成功（DuckDB）",
                "view_name": request.view_name,
                "dataset_id": dataset.id
            }
        
        else:
            # 传统数据源模式
            logger.info(f"Using DataSource ID: {request.datasource_id}")
            
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
    
    # 2. 删除所有关联的外键记录（修复外键约束错误）
    from app.models.metadata import ChatMessage, ChatSession, DashboardCard, ComputedMetric
    
    # 删除关联的聊天消息
    db.query(ChatMessage).filter(ChatMessage.dataset_id == id).delete()
    
    # 删除关联的聊天会话（将 dataset_id 设为 NULL，因为它是可选的）
    db.query(ChatSession).filter(ChatSession.dataset_id == id).update(
        {"dataset_id": None}
    )
    
    # 删除关联的看板卡片
    db.query(DashboardCard).filter(DashboardCard.dataset_id == id).delete()
    
    # 删除关联的计算指标
    db.query(ComputedMetric).filter(ComputedMetric.dataset_id == id).delete()
    
    # 3. 删除数据库记录（级联删除会自动删除 business_terms 和 training_logs）
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

            # 如果有关系被训练，清理缓存
            if train_result["trained_count"] > 0:
                VannaManager.clear_cache(id)

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


@router.post("/upload_quick_analysis", response_model=DatasetResponse)
async def upload_file_for_quick_analysis(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传 Excel/CSV 文件并自动创建数据集进行快速分析
    
    处理流程:
    1. 读取文件为 DataFrame
    2. 清洗列名以兼容 SQL
    3. 将数据写入第一个可用数据源
    4. 创建 Dataset 记录
    5. 自动训练 DDL
    
    Args:
        file: 上传的文件 (CSV/Excel)
        name: 数据集名称（可选，默认为文件名）
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        DatasetResponse: 新创建的数据集信息
    """
    import logging
    from app.utils.file_handler import read_file_to_df, sanitize_column_names
    from app.services.db_inspector import DBInspector
    from app.services.vanna import VannaTrainingService
    
    logger = logging.getLogger(__name__)
    
    # 1. 读取文件为 DataFrame
    logger.info(f"Reading uploaded file: {file.filename}")
    df = read_file_to_df(file)
    
    # 2. 清洗列名
    df = sanitize_column_names(df)
    logger.info(f"Sanitized columns: {list(df.columns)}")
    
    # 3. 获取第一个可用的数据源（优先选择用户自己的）
    datasource_query = db.query(DataSource)
    datasource_query = apply_ownership_filter(datasource_query, DataSource, current_user)
    datasource = datasource_query.first()
    
    if not datasource:
        # 如果用户没有数据源，尝试获取系统默认数据源（owner_id 为 None）
        datasource = db.query(DataSource).filter(DataSource.owner_id == None).first()
    
    if not datasource:
        raise HTTPException(
            status_code=400, 
            detail="没有可用的数据源，请先创建一个数据库连接"
        )
    
    # 4. 生成唯一表名
    timestamp = int(time.time())
    table_name = f"upload_{current_user.id}_{timestamp}"
    logger.info(f"Generated table name: {table_name}")
    
    try:
        # 5. 将 DataFrame 写入数据库
        engine = DBInspector.get_engine(datasource)
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists='replace',
            index=False,
            method='multi'  # 批量插入提高性能
        )
        logger.info(f"Successfully wrote {len(df)} rows to table {table_name}")
        
    except Exception as e:
        logger.error(f"Failed to write data to database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"数据写入数据库失败: {str(e)}"
        )
    
    # 6. 创建 Dataset 记录
    dataset_name = name or file.filename.rsplit('.', 1)[0]  # 默认使用文件名
    
    dataset = Dataset(
        name=dataset_name,
        datasource_id=datasource.id,
        schema_config=[table_name],  # 自动配置表
        status="pending",
        owner_id=current_user.id
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # 自动生成 collection_name
    dataset.collection_name = f"vec_ds_{dataset.id}"
    db.commit()
    db.refresh(dataset)
    
    logger.info(f"Created dataset {dataset.id} with table {table_name}")
    
    # 7. 自动训练 DDL（简易训练）
    try:
        logger.info(f"Starting quick training for dataset {dataset.id}")
        
        # 获取 DDL
        ddl = DBInspector.get_table_ddl(datasource, table_name)
        
        # 使用 Legacy Vanna 训练 DDL
        from app.services.vanna.instance_manager import VannaInstanceManager
        vn = VannaInstanceManager.get_legacy_vanna(dataset.id)
        vn.train(ddl=ddl)
        
        # 更新状态
        dataset.status = "completed"
        dataset.process_rate = 100
        dataset.last_train_at = datetime.utcnow()
        db.commit()
        db.refresh(dataset)
        
        logger.info(f"Quick training completed for dataset {dataset.id}")
        
    except Exception as e:
        logger.error(f"Training failed for dataset {dataset.id}: {e}")
        dataset.status = "failed"
        dataset.error_msg = str(e)
        db.commit()
        db.refresh(dataset)
    
    return dataset


@router.get("/{id}/suggested_questions", response_model=SuggestedQuestions)
async def get_suggested_questions(
    id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据集的推荐问题（猜你想问）
    
    该功能根据数据集的表结构和关键字段，利用 LLM 生成用户最可能感兴趣的业务分析问题。
    结果会缓存 24 小时，减少 LLM 调用成本。
    
    Args:
        id: 数据集 ID
        limit: 返回问题数量（默认 5）
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        SuggestedQuestions: 包含问题列表的响应
    """
    # 验证 dataset 访问权限
    query = db.query(Dataset).filter(Dataset.id == id)
    query = apply_ownership_filter(query, Dataset, current_user)
    dataset = query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 缓存 Key
    cache_key = f"suggested_questions:{id}:{limit}"
    
    try:
        # 检查 Redis 缓存
        from app.core.redis import redis_service
        cached_questions = await redis_service.get(cache_key)
        
        if cached_questions:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Returning cached suggested questions for dataset {id}")
            return SuggestedQuestions(questions=cached_questions)
        
        # 生成推荐问题
        questions = VannaManager.generate_suggested_questions(
            dataset_id=id,
            db_session=db,
            limit=limit
        )
        
        # 存入 Redis 缓存（24 小时过期）
        cache_ttl = 86400  # 24 hours
        await redis_service.set(cache_key, questions, expire=cache_ttl)
        
        return SuggestedQuestions(questions=questions)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate suggested questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成推荐问题失败: {str(e)}")


# ==================== 计算指标 CRUD ====================

from pydantic import BaseModel

class ComputedMetricCreate(BaseModel):
    """Create computed metric request"""
    name: str
    formula: str
    description: Optional[str] = None

class ComputedMetricResponse(BaseModel):
    """Computed metric response"""
    id: int
    dataset_id: int
    name: str
    formula: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/{id}/metrics", response_model=List[ComputedMetricResponse])
def get_computed_metrics(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all computed metrics for a dataset.
    应用数据隔离：只能查看自己的数据集的指标
    """
    # 验证 dataset 访问权限
    dataset_query = db.query(Dataset).filter(Dataset.id == id)
    dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
    dataset = dataset_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 获取所有计算指标
    metrics = db.query(ComputedMetric).filter(ComputedMetric.dataset_id == id).all()
    return metrics


@router.post("/{id}/metrics", response_model=ComputedMetricResponse)
def create_computed_metric(
    id: int,
    metric_in: ComputedMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new computed metric for a dataset.
    应用数据隔离：需要验证 Dataset 的所有权
    """
    # 验证 dataset 访问权限
    dataset_query = db.query(Dataset).filter(Dataset.id == id)
    dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
    dataset = dataset_query.first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    # 创建计算指标
    metric = ComputedMetric(
        dataset_id=id,
        name=metric_in.name,
        formula=metric_in.formula,
        description=metric_in.description,
        owner_id=current_user.id
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    
    return metric


@router.put("/metrics/{metric_id}", response_model=ComputedMetricResponse)
def update_computed_metric(
    metric_id: int,
    metric_in: ComputedMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a computed metric.
    应用数据隔离：只能更新自己的指标
    """
    # 查找指标
    metric = db.query(ComputedMetric).filter(ComputedMetric.id == metric_id).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    # 验证权限：需要验证 dataset 的访问权限
    dataset_query = db.query(Dataset).filter(Dataset.id == metric.dataset_id)
    dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
    dataset = dataset_query.first()
    
    if not dataset:
        raise HTTPException(status_code=403, detail="Access denied to this metric")
    
    # 更新指标
    metric.name = metric_in.name
    metric.formula = metric_in.formula
    metric.description = metric_in.description
    metric.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(metric)
    
    return metric


@router.delete("/metrics/{metric_id}")
def delete_computed_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a computed metric.
    应用数据隔离：只能删除自己的指标
    """
    # 查找指标
    metric = db.query(ComputedMetric).filter(ComputedMetric.id == metric_id).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    # 验证权限：需要验证 dataset 的访问权限
    dataset_query = db.query(Dataset).filter(Dataset.id == metric.dataset_id)
    dataset_query = apply_ownership_filter(dataset_query, Dataset, current_user)
    dataset = dataset_query.first()
    
    if not dataset:
        raise HTTPException(status_code=403, detail="Access denied to this metric")
    
    # 删除指标
    db.delete(metric)
    db.commit()
    
    return {"message": f"指标 {metric.name} 已删除"}
