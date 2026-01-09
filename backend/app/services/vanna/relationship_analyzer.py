"""
RelationshipAnalyzer - LLM 增强的表关系分析器
综合利用规则引擎、数据采样和 LLM 推理来识别表之间的关联关系
"""
import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import inspect, select, func, text, MetaData, Table
from sqlalchemy.engine import Engine

from app.core.logger import get_logger
from app.services.duckdb_service import DuckDBService
from app.core.config import settings
from openai import OpenAI as OpenAIClient

logger = get_logger(__name__)


class RelationshipAnalyzer:
    """LLM 增强的表关系分析器
    
    提供三层分析：
    1. 规则初筛：基于命名模式和数据类型
    2. LLM 深度分析：理解业务语义
    3. 数据重合度验证：计算实际数据交集
    """
    
    @classmethod
    def analyze_relationships(
        cls,
        dataset_id: int,
        table_names: List[str],
        db_path: Optional[str] = None,
        engine: Optional[Engine] = None
    ) -> List[Dict[str, Any]]:
        """分析表之间的关系
        
        Args:
            dataset_id: 数据集 ID
            table_names: 表名列表
            db_path: DuckDB 数据库路径 (可选)
            engine: SQLAlchemy Engine (可选)
            
        Returns:
            List[Dict]: 推荐的关系列表
        """
        if not db_path and not engine:
            raise ValueError("Must provide either db_path or engine")

        logger.info(
            f"Starting relationship analysis for dataset {dataset_id}",
            table_count=len(table_names)
        )
        
        if len(table_names) < 2:
            logger.warning("Need at least 2 tables to analyze relationships")
            return []
        
        try:
            # Step 1: 提取表 Schema 和采样数据
            schemas = cls._extract_schemas(table_names, db_path, engine)
            
            # Step 2: 规则初筛（快速剔除明显不相关的）
            candidates = cls._rule_based_filtering(schemas)
            
            logger.info(f"Rule-based filtering found {len(candidates)} candidate relationships")
            
            # Step 3: LLM 深度分析
            if len(candidates) > 0:
                relationships = cls._llm_analysis(schemas, candidates)
            else:
                # 如果规则没找到，直接让 LLM 分析
                relationships = cls._llm_analysis(schemas, [])
            
            logger.info(f"LLM analysis identified {len(relationships)} relationships")
            
            # Step 4: 数据重合度验证（对高置信度关系）
            for rel in relationships:
                if rel.get('confidence') in ['high', 'medium']:
                    try:
                        overlap = cls._calculate_data_overlap(
                            rel['source'],
                            rel['source_col'],
                            rel['target'],
                            rel['target_col'],
                            db_path,
                            engine
                        )
                        rel['data_overlap'] = overlap
                        
                        # 根据重合度调整置信度
                        if overlap < 50 and rel['confidence'] == 'high':
                            rel['confidence'] = 'medium'
                            rel['reasoning'] += f"（数据重合度较低：{overlap:.1f}%）"
                        
                    except Exception as e:
                        logger.warning(f"Failed to calculate overlap for {rel}: {e}")
                        rel['data_overlap'] = None
            
            logger.info(
                f"Relationship analysis completed",
                dataset_id=dataset_id,
                relationships_found=len(relationships)
            )
            
            return relationships
        
        except Exception as e:
            logger.error(f"Relationship analysis failed: {e}", exc_info=True)
            raise
    
    @classmethod
    def _extract_schemas(
        cls,
        table_names: List[str],
        db_path: Optional[str] = None,
        engine: Optional[Engine] = None
    ) -> List[Dict[str, Any]]:
        """提取表的 Schema 和采样数据"""
        if db_path:
            return cls._extract_schemas_from_duckdb(db_path, table_names)
        elif engine:
            return cls._extract_schemas_from_engine(engine, table_names)
        else:
            raise ValueError("No database connection provided")

    @classmethod
    def _extract_schemas_from_duckdb(
        cls,
        db_path: str,
        table_names: List[str]
    ) -> List[Dict[str, Any]]:
        schemas = []
        
        for table in table_names:
            try:
                # 获取 Schema
                schema = DuckDBService.get_table_schema(db_path, table)
                
                # 获取采样数据（前 100 行）
                sample_df = DuckDBService.get_table_sample(db_path, table, limit=100)
                
                # 获取统计信息
                stats = DuckDBService.get_table_statistics(db_path, table)
                
                # 转换DataFrame为字典，并处理不可序列化的类型（如Timestamp）
                sample_data_dict = sample_df.head(5).to_dict('records')
                
                # 修复：将Timestamp等pandas类型转换为字符串
                import pandas as pd
                for row in sample_data_dict:
                    for key, value in row.items():
                        if isinstance(value, (pd.Timestamp, pd.Timedelta)):
                            row[key] = str(value)
                        elif pd.isna(value):
                            row[key] = None
                
                schemas.append({
                    "table_name": table,
                    "columns": schema,
                    "sample_data": sample_data_dict,
                    "statistics": stats
                })
                
                logger.debug(f"Extracted schema for {table}: {len(schema)} columns, {stats['row_count']} rows")
            
            except Exception as e:
                logger.error(f"Failed to extract schema for {table}: {e}")
                raise
        
        return schemas

    @classmethod
    def _extract_schemas_from_engine(
        cls,
        engine: Engine,
        table_names: List[str]
    ) -> List[Dict[str, Any]]:
        schemas = []
        inspector = inspect(engine)
        
        for table_name in table_names:
            try:
                # Get Columns
                columns = inspector.get_columns(table_name)
                # Normalize column info to match DuckDB format
                schema = []
                for col in columns:
                    schema.append({
                        "name": col['name'],
                        "type": str(col['type']),
                        "nullable": col.get('nullable', True)
                    })

                # Get Sample Data
                # Use pandas for easier type handling
                query = text(f"SELECT * FROM {engine.dialect.identifier_preparer.quote(table_name)}")
                # Note: LIMIT syntax varies by dialect, but pandas head() handles it after fetching or we can append limit
                # Ideally we should use select().limit()
                
                try:
                    metadata = MetaData()
                    table_obj = Table(table_name, metadata, autoload_with=engine)
                    stmt = select(table_obj).limit(100)
                    sample_df = pd.read_sql(stmt, engine)
                except Exception:
                    # Fallback to raw SQL if reflection fails
                    sample_df = pd.read_sql(query, engine).head(100)

                # Get Statistics (Row Count)
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {engine.dialect.identifier_preparer.quote(table_name)}")
                    with engine.connect() as conn:
                        row_count = conn.execute(count_query).scalar()
                except Exception:
                    row_count = len(sample_df) # Fallback

                stats = {"row_count": row_count}

                # Serialize sample data
                sample_data_dict = sample_df.head(5).to_dict('records')
                for row in sample_data_dict:
                    for key, value in row.items():
                        if isinstance(value, (pd.Timestamp, pd.Timedelta)):
                            row[key] = str(value)
                        elif pd.isna(value):
                            row[key] = None

                schemas.append({
                    "table_name": table_name,
                    "columns": schema,
                    "sample_data": sample_data_dict,
                    "statistics": stats
                })

            except Exception as e:
                logger.error(f"Failed to extract schema for {table_name} from engine: {e}")
                raise
        
        return schemas
    
    @classmethod
    def _rule_based_filtering(
        cls,
        schemas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基于规则的关系初筛
        
        规则：
        1. 命名模式：table_id 关联 table.id
        2. 数据类型兼容
        3. 唯一值比例合理
        """
        candidates = []
        
        for i, schema_a in enumerate(schemas):
            for schema_b in schemas[i+1:]:
                table_a = schema_a['table_name']
                table_b = schema_b['table_name']
                
                # 检查每对列
                for col_a in schema_a['columns']:
                    for col_b in schema_b['columns']:
                        # 跳过同名列（可能是不同表的相同维度）
                        if col_a['name'] == col_b['name']:
                            continue
                        
                        # 规则1: 命名模式匹配
                        is_naming_match = cls._check_naming_pattern(
                            table_a, col_a['name'],
                            table_b, col_b['name']
                        )
                        
                        # 规则2: 数据类型兼容
                        is_type_compatible = cls._check_type_compatibility(
                            col_a['type'], col_b['type']
                        )
                        
                        if is_naming_match and is_type_compatible:
                            # 确定方向：通常 id 列是被引用的（target）
                            if col_b['name'] == 'id' or col_b['name'].endswith('_id'):
                                source, source_col = table_a, col_a['name']
                                target, target_col = table_b, col_b['name']
                            else:
                                source, source_col = table_b, col_b['name']
                                target, target_col = table_a, col_a['name']
                            
                            candidates.append({
                                "source": source,
                                "target": target,
                                "source_col": source_col,
                                "target_col": target_col,
                                "confidence": "medium",
                                "reasoning": "命名模式匹配 + 数据类型兼容"
                            })
        
        # 去重
        unique_candidates = []
        seen = set()
        for cand in candidates:
            key = f"{cand['source']}.{cand['source_col']}-{cand['target']}.{cand['target_col']}"
            if key not in seen:
                seen.add(key)
                unique_candidates.append(cand)
        
        return unique_candidates
    
    @classmethod
    def _check_naming_pattern(
        cls,
        table_a: str,
        col_a: str,
        table_b: str,
        col_b: str
    ) -> bool:
        """检查列名是否符合外键命名模式
        
        常见模式：
        - orders.customer_id -> customers.id
        - orders.user_id -> users.id
        - order_items.order_id -> orders.id
        """
        col_a_lower = col_a.lower()
        col_b_lower = col_b.lower()
        table_a_lower = table_a.lower()
        table_b_lower = table_b.lower()
        
        # 模式1: col_a 包含 table_b 名称
        # 例如：customer_id 包含 customer
        if table_b_lower in col_a_lower and col_b_lower == 'id':
            return True
        
        # 模式2: col_b 包含 table_a 名称
        if table_a_lower in col_b_lower and col_a_lower == 'id':
            return True
        
        # 模式3: 单数/复数变化
        # customers.id -> customer_id
        singular_b = table_b_lower.rstrip('s')
        if f"{singular_b}_id" == col_a_lower and col_b_lower == 'id':
            return True
        
        singular_a = table_a_lower.rstrip('s')
        if f"{singular_a}_id" == col_b_lower and col_a_lower == 'id':
            return True
        
        return False
    
    @classmethod
    def _check_type_compatibility(cls, type_a: str, type_b: str) -> bool:
        """检查两个列的数据类型是否兼容"""
        type_a_lower = type_a.lower()
        type_b_lower = type_b.lower()
        
        # 数值类型组
        numeric_types = ['integer', 'int', 'bigint', 'smallint', 'tinyint', 'int64', 'int32']
        
        # 字符串类型组
        string_types = ['varchar', 'char', 'text', 'string']
        
        # 浮点类型组
        float_types = ['float', 'double', 'decimal', 'numeric', 'real']
        
        # 检查是否在同一类型组
        if any(t in type_a_lower for t in numeric_types) and any(t in type_b_lower for t in numeric_types):
            return True
        
        if any(t in type_a_lower for t in string_types) and any(t in type_b_lower for t in string_types):
            return True
        
        if any(t in type_a_lower for t in float_types) and any(t in type_b_lower for t in float_types):
            return True
        
        return False
    
    @classmethod
    def _llm_analysis(
        cls,
        schemas: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """使用 LLM 进行深度关系分析"""
        prompt = cls._build_analysis_prompt(schemas, candidates)
        
        try:
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个数据库关系分析专家。你擅长识别表之间的外键关系，理解业务语义，并给出清晰的推理依据。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1
            )
            
            llm_response = response.choices[0].message.content
            logger.debug(f"LLM response: {llm_response[:500]}...")
            
            # 解析 LLM 返回的 JSON
            relationships = cls._parse_llm_response(llm_response)
            
            return relationships
        
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            # 如果 LLM 失败，返回规则初筛的结果
            return candidates
    
    @classmethod
    def _build_analysis_prompt(
        cls,
        schemas: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> str:
        """构建 LLM 分析 Prompt"""
        
        # 精简 schema 信息（只保留必要字段）
        simplified_schemas = []
        for schema in schemas:
            simplified_schemas.append({
                "table_name": schema['table_name'],
                "columns": [
                    {
                        "name": col['name'],
                        "type": col['type']
                    }
                    for col in schema['columns']
                ],
                "row_count": schema['statistics']['row_count'],
                "sample_values": {
                    col['name']: [
                        row.get(col['name'])
                        for row in schema['sample_data'][:3]
                        if row.get(col['name']) is not None
                    ][:3]
                    for col in schema['columns'][:5]  # 只取前5列的样本
                }
            })
        
        prompt = f"""分析以下数据表结构，识别潜在的外键关系：

**表结构信息：**
{json.dumps(simplified_schemas, ensure_ascii=False, indent=2)}

"""
        
        if candidates:
            prompt += f"""
**已通过规则初筛的候选关系：**
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请基于以上候选关系，结合业务语义进行深度分析，确认或调整这些关系。
"""
        else:
            prompt += """
规则引擎未找到明显的命名模式匹配，请基于业务逻辑和数据特征推断可能的关系。
"""
        
        prompt += """
**分析维度：**
1. **命名约定**：例如 orders.customer_id 应关联到 customers.id
2. **数据类型**：确保字段类型兼容（INT-INT, VARCHAR-VARCHAR）
3. **业务逻辑**：理解订单、客户、产品等常见实体关系
4. **样本数据**：观察实际数据值的模式

**要求：**
- 严格返回 JSON 数组（无任何其他文本、无 Markdown 代码块）
- 如果没有找到任何关系，返回空数组：[]
- 每个关系必须包含明确的推理依据

**返回格式：**
[
  {
    "source": "表A",
    "target": "表B",
    "source_col": "列A",
    "target_col": "列B",
    "type": "left",
    "confidence": "high",
    "reasoning": "推理依据（中文，简洁明了）"
  }
]

你的分析结果："""
        
        return prompt
    
    @classmethod
    def _parse_llm_response(cls, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的 JSON"""
        try:
            # 去除可能的 Markdown 代码块标记
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # 解析 JSON
            relationships = json.loads(response)
            
            if not isinstance(relationships, list):
                logger.warning(f"LLM response is not a list: {type(relationships)}")
                return []
            
            # 验证每个关系的必需字段
            valid_relationships = []
            required_fields = ['source', 'target', 'source_col', 'target_col']
            
            for rel in relationships:
                if all(field in rel for field in required_fields):
                    # 填充默认值
                    rel.setdefault('type', 'left')
                    rel.setdefault('confidence', 'medium')
                    rel.setdefault('reasoning', '基于 LLM 分析')
                    valid_relationships.append(rel)
                else:
                    logger.warning(f"Relationship missing required fields: {rel}")
            
            return valid_relationships
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {response[:500]}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    @classmethod
    def _calculate_data_overlap(
        cls,
        table_a: str,
        col_a: str,
        table_b: str,
        col_b: str,
        db_path: Optional[str] = None,
        engine: Optional[Engine] = None
    ) -> float:
        """计算两列数据的重合度（Jaccard 相似度）
        
        Returns:
            float: 重合度百分比 (0-100)
        """
        if db_path:
            return cls._calculate_data_overlap_duckdb(db_path, table_a, col_a, table_b, col_b)
        elif engine:
            return cls._calculate_data_overlap_engine(engine, table_a, col_a, table_b, col_b)
        else:
            raise ValueError("No database connection provided")

    @classmethod
    def _calculate_data_overlap_duckdb(
        cls,
        db_path: str,
        table_a: str,
        col_a: str,
        table_b: str,
        col_b: str
    ) -> float:
        try:
            sql = f"""
            WITH a_values AS (
                SELECT DISTINCT "{col_a}" AS val FROM "{table_a}" WHERE "{col_a}" IS NOT NULL
            ),
            b_values AS (
                SELECT DISTINCT "{col_b}" AS val FROM "{table_b}" WHERE "{col_b}" IS NOT NULL
            ),
            intersection AS (
                SELECT COUNT(*) as cnt 
                FROM a_values 
                INNER JOIN b_values ON a_values.val = b_values.val
            ),
            union_count AS (
                SELECT COUNT(*) as cnt 
                FROM (
                    SELECT val FROM a_values 
                    UNION 
                    SELECT val FROM b_values
                )
            )
            SELECT 
                CASE 
                    WHEN union_count.cnt = 0 THEN 0
                    ELSE (intersection.cnt * 100.0 / union_count.cnt)
                END AS overlap_percent
            FROM intersection, union_count
            """
            
            result_df = DuckDBService.execute_query(db_path, sql, read_only=True)
            overlap = float(result_df.iloc[0, 0])
            
            logger.debug(
                f"Data overlap (DuckDB): {table_a}.{col_a} <-> {table_b}.{col_b} = {overlap:.1f}%"
            )
            
            return round(overlap, 2)
        
        except Exception as e:
            logger.error(f"Failed to calculate data overlap in DuckDB: {e}", exc_info=True)
            raise

    @classmethod
    def _calculate_data_overlap_engine(
        cls,
        engine: Engine,
        table_a: str,
        col_a: str,
        table_b: str,
        col_b: str
    ) -> float:
        try:
            # Quote identifiers for safety
            q_table_a = engine.dialect.identifier_preparer.quote(table_a)
            q_col_a = engine.dialect.identifier_preparer.quote(col_a)
            q_table_b = engine.dialect.identifier_preparer.quote(table_b)
            q_col_b = engine.dialect.identifier_preparer.quote(col_b)

            # Use standard SQL CTEs which are supported by most modern DBs (MySQL 8.0+, PG, etc.)
            # Note: Older MySQL versions (<8.0) do not support CTEs. 
            # If we need to support them, we'd need nested subqueries.
            # Assuming modern environment here.
            
            sql = text(f"""
            WITH a_values AS (
                SELECT DISTINCT {q_col_a} AS val FROM {q_table_a} WHERE {q_col_a} IS NOT NULL
            ),
            b_values AS (
                SELECT DISTINCT {q_col_b} AS val FROM {q_table_b} WHERE {q_col_b} IS NOT NULL
            ),
            intersection AS (
                SELECT COUNT(*) as cnt 
                FROM a_values 
                INNER JOIN b_values ON a_values.val = b_values.val
            ),
            union_count AS (
                SELECT COUNT(*) as cnt 
                FROM (
                    SELECT val FROM a_values 
                    UNION 
                    SELECT val FROM b_values
                ) as u
            )
            SELECT 
                CASE 
                    WHEN union_count.cnt = 0 THEN 0
                    ELSE (intersection.cnt * 100.0 / union_count.cnt)
                END AS overlap_percent
            FROM intersection, union_count
            """)
            
            with engine.connect() as conn:
                result = conn.execute(sql).scalar()
                overlap = float(result) if result is not None else 0.0
            
            logger.debug(
                f"Data overlap (SQLAlchemy): {table_a}.{col_a} <-> {table_b}.{col_b} = {overlap:.1f}%"
            )
            
            return round(overlap, 2)
        
        except Exception as e:
            logger.error(f"Failed to calculate data overlap with Engine: {e}", exc_info=True)
            # Return 0 or None? Original logic returns None on error in loop, 
            # but here we raise so the loop can catch it and set to None.
            raise
