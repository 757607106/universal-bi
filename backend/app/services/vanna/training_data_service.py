"""
Vanna 训练数据服务

提供训练数据的 CRUD 操作。
"""

import re
import json

from app.core.config import settings
from app.core.logger import get_logger
from app.services.vanna.instance_manager import VannaInstanceManager
from app.services.vanna.cache_service import VannaCacheService

logger = get_logger(__name__)


class VannaTrainingDataService:
    """
    训练数据 CRUD 服务

    提供训练数据的查询、删除等操作。
    使用 PGVector 后端存储向量数据。
    """

    @classmethod
    def get_training_data(cls, dataset_id: int, page: int = 1, page_size: int = 20, type_filter: str = None) -> dict:
        """
        获取训练数据（QA对、DDL、文档等）
        使用 PGVector 后端

        Args:
            dataset_id: 数据集ID
            page: 页码（从1开始）
            page_size: 每页数量
            type_filter: 类型筛选，可选值: 'ddl', 'sql', 'documentation', None(全部)

        Returns:
            dict: {
                'total': int,
                'items': [...],
                'page': int,
                'page_size': int
            }
        """
        return cls._get_training_data_pgvector(dataset_id, page, page_size, type_filter)

    @classmethod
    def _get_training_data_pgvector(cls, dataset_id: int, page: int = 1, page_size: int = 20, type_filter: str = None) -> dict:
        """
        从 PGVector 获取训练数据
        """
        try:
            # 获取 Vanna 实例（PGVector 后端）
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)

            # 使用 Vanna 的 get_training_data 方法
            df = vn.get_training_data()

            all_items = []

            if df is not None and not df.empty:
                # Fill NaN values with empty string to avoid validation errors
                df = df.fillna('')

                for _, row in df.iterrows():
                    doc_id = row.get('id', '')
                    content = row.get('content', '')
                    training_data_type = row.get('training_data_type', 'sql')
                    question = row.get('question', '')

                    # 应用类型筛选
                    if type_filter and type_filter != 'all' and training_data_type != type_filter:
                        continue

                    # 处理 question
                    if not question:
                        question = cls._extract_question_from_content(content, training_data_type)

                    all_items.append({
                        'id': str(doc_id),
                        'question': question or '未命名',
                        'sql': content,
                        'training_data_type': training_data_type,
                        'created_at': None
                    })

            # 计算分页
            total = len(all_items)
            start = (page - 1) * page_size
            end = start + page_size
            items = all_items[start:end]

            logger.info(f"Retrieved {len(items)} training data items from PGVector (page {page}/{(total + page_size - 1) // page_size if total > 0 else 1}) for dataset {dataset_id}")

            return {
                'total': total,
                'items': items,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"Failed to get training data from PGVector for dataset {dataset_id}: {e}")
            raise ValueError(f"获取训练数据失败: {str(e)}")

    @classmethod
    def _get_training_data_chromadb(cls, dataset_id: int, page: int = 1, page_size: int = 20, type_filter: str = None) -> dict:
        """
        从 ChromaDB 获取训练数据
        支持分页查询，兼容旧版和新版存储格式
        """
        collection_name = f"vec_ds_{dataset_id}"

        try:
            # 获取全局 ChromaDB 客户端
            chroma_client = VannaInstanceManager._get_global_chroma_client()

            all_items = []

            # 方案 1：新版分开存储的 collection
            if type_filter and type_filter != 'all':
                collection_configs = [(f"{collection_name}_{type_filter}", type_filter)]
            else:
                collection_configs = [
                    (f"{collection_name}_ddl", 'ddl'),
                    (f"{collection_name}_documentation", 'documentation'),
                    (f"{collection_name}_sql", 'sql'),
                ]

            for coll_name, data_type in collection_configs:
                try:
                    collection = chroma_client.get_collection(name=coll_name)
                    result = collection.get(include=['documents', 'metadatas'])

                    ids = result.get('ids', [])
                    documents = result.get('documents', [])
                    metadatas = result.get('metadatas', [])

                    for i, doc_id in enumerate(ids):
                        document = documents[i] if i < len(documents) else ''
                        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}

                        # 处理 metadata 中的 question
                        question = metadata.get('question', '')
                        if isinstance(question, str) and question.startswith('{'):
                            try:
                                parsed = json.loads(question)
                                question = parsed.get('question', '')
                            except:
                                pass

                        # 处理 document
                        sql = document
                        if isinstance(sql, str) and sql.startswith('{'):
                            try:
                                parsed = json.loads(sql)
                                question = parsed.get('question', question)
                                sql = parsed.get('sql', sql)
                            except:
                                pass

                        training_data_type = data_type

                        # 提取 question
                        if not question:
                            question = cls._extract_question_from_content(sql, training_data_type)

                        all_items.append({
                            'id': doc_id,
                            'question': question or '未命名',
                            'sql': sql,
                            'training_data_type': training_data_type,
                            'created_at': metadata.get('created_at') or metadata.get('timestamp')
                        })

                except Exception as e:
                    if "does not exist" not in str(e).lower():
                        logger.warning(f"Failed to get data from collection {coll_name}: {e}")
                    continue

            # 方案 2：旧版单一 collection 格式（兼容旧数据）
            if len(all_items) == 0:
                try:
                    collection = chroma_client.get_collection(name=collection_name)
                    result = collection.get(include=['documents', 'metadatas'])

                    ids = result.get('ids', [])
                    documents = result.get('documents', [])
                    metadatas = result.get('metadatas', [])

                    for i, doc_id in enumerate(ids):
                        document = documents[i] if i < len(documents) else ''
                        metadata = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}

                        question = metadata.get('question', '')
                        sql = document

                        # 自动检测数据类型
                        training_data_type = 'sql'
                        if 'CREATE TABLE' in document.upper() or 'CREATE VIEW' in document.upper():
                            training_data_type = 'ddl'
                        elif question is None or question == '':
                            if '业务' in document or 'joined with' in document.lower():
                                training_data_type = 'documentation'

                        # 应用类型筛选
                        if type_filter and type_filter != 'all' and training_data_type != type_filter:
                            continue

                        # 提取 question
                        if not question:
                            question = cls._extract_question_from_content(sql, training_data_type)

                        all_items.append({
                            'id': doc_id,
                            'question': question,
                            'sql': sql,
                            'training_data_type': training_data_type,
                            'created_at': metadata.get('created_at') or metadata.get('timestamp')
                        })

                except Exception as e:
                    if "does not exist" not in str(e).lower():
                        logger.warning(f"Failed to get data from legacy collection {collection_name}: {e}")

            # 计算分页
            total = len(all_items)
            start = (page - 1) * page_size
            end = start + page_size
            items = all_items[start:end]

            logger.info(f"Retrieved {len(items)} training data items from ChromaDB (page {page}/{(total + page_size - 1) // page_size if total > 0 else 1}) for dataset {dataset_id}")

            return {
                'total': total,
                'items': items,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"Failed to get training data from ChromaDB for dataset {dataset_id}: {e}")
            raise ValueError(f"获取训练数据失败: {str(e)}")

    @classmethod
    def _extract_question_from_content(cls, content: str, training_data_type: str) -> str:
        """
        从内容中提取 question 字段
        """
        if not content:
            return "未命名"

        # DDL 类型：使用表名作为 question
        if training_data_type == 'ddl':
            table_match = re.search(r'CREATE TABLE\s+`?(\w+)`?', content, re.IGNORECASE)
            if table_match:
                return f"表结构: {table_match.group(1)}"
            return "数据库表结构定义"

        # 文档类型
        if training_data_type == 'documentation':
            if '业务术语' in content:
                term_match = re.search(r'业务术语[：:]\s*(.+?)\n', content)
                if term_match:
                    return term_match.group(1)
                return "业务术语定义"
            elif 'joined with' in content.lower():
                relation_match = re.search(r'`(\w+)`.*?joined with.*?`(\w+)`', content, re.IGNORECASE)
                if relation_match:
                    return f"{relation_match.group(1)} 与 {relation_match.group(2)} 的关系"
                return "表关系描述"
            else:
                return content[:50].strip() if len(content) > 50 else content.strip()

        # SQL QA 对
        if training_data_type == 'sql':
            # 尝试从内容中提取 Question 部分
            question_match = re.search(r'Question:\s*(.+?)(?:\n|SQL:)', content, re.IGNORECASE)
            if question_match:
                return question_match.group(1).strip()
            return "示例查询"

        return "未命名"

    @classmethod
    def remove_training_data(cls, dataset_id: int, training_data_id: str) -> bool:
        """
        删除单条训练数据
        使用 PGVector 后端
    
        Args:
            dataset_id: 数据集ID
            training_data_id: 训练数据 ID
    
        Returns:
            bool: 是否成功删除
        """
        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            success = vn.remove_training_data(training_data_id)

            if success:
                logger.info(f"Removed training data {training_data_id} from dataset {dataset_id}")
                # 注意：缓存清理应在调用方的异步上下文中处理
            else:
                logger.warning(f"Failed to remove training data {training_data_id} - ID not found or invalid format")

            return success

        except Exception as e:
            logger.error(f"Failed to remove training data {training_data_id} from dataset {dataset_id}: {e}")
            return False

    @classmethod
    async def remove_training_data_async(cls, dataset_id: int, training_data_id: str) -> bool:
        """
        异步删除单条训练数据，包含缓存清理

        Args:
            dataset_id: 数据集ID
            training_data_id: 训练数据ID

        Returns:
            bool: 是否成功删除
        """
        success = cls.remove_training_data(dataset_id, training_data_id)

        if success:
            # 清理缓存
            cleared = await VannaCacheService.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after removing training data")

        return success
