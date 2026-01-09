"""
Vanna 训练服务

提供数据集训练、业务术语训练、表关系训练等功能。
"""

import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.metadata import Dataset, TrainingLog, BusinessTerm
from app.core.logger import get_logger
from app.services.db_inspector import DBInspector
from app.services.duckdb_service import DuckDBService
from app.services.vanna.base import TrainingStoppedException
from app.services.vanna.instance_manager import VannaInstanceManager
from app.services.vanna.cache_service import VannaCacheService

logger = get_logger(__name__)


class VannaTrainingService:
    """
    Vanna 训练服务

    提供数据集训练、业务术语训练、表关系训练、问答对训练等功能。
    """

    @classmethod
    def _checkpoint_and_check_interrupt(cls, db_session: Session, dataset_id: int, progress: int, log_message: str):
        """
        检查点：更新进度、记录日志、检查中断

        Args:
            db_session: 数据库会话
            dataset_id: 数据集ID
            progress: 当前进度 (0-100)
            log_message: 日志消息

        Raises:
            TrainingStoppedException: 如果状态为 paused
        """
        # 1. 更新进度
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        dataset.process_rate = progress

        # 2. 记录日志
        training_log = TrainingLog(
            dataset_id=dataset_id,
            content=f"[{progress}%] {log_message}"
        )
        db_session.add(training_log)
        db_session.commit()
        db_session.refresh(dataset)  # 刷新以获取最新状态

        logger.info(f"Checkpoint: Dataset {dataset_id} progress {progress}% - {log_message}")

        # 3. 检查是否被中断
        if dataset.status == "paused":
            logger.warning(f"Training interrupted by user for dataset {dataset_id}")
            raise TrainingStoppedException(f"训练被用户中断 (Dataset {dataset_id})")

    @classmethod
    def train_dataset(cls, dataset_id: int, table_names: list[str], db_session: Session):
        """
        Train the dataset by extracting DDLs and feeding them to Vanna Memory.
        This wrapper handles the sync-to-async bridge.
        """
        # 在训练前主动清理该数据集的缓存，避免 ChromaDB 实例冲突
        VannaInstanceManager.clear_instance_cache(dataset_id)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(cls.train_dataset_async(dataset_id, table_names, db_session))

    @classmethod
    async def train_dataset_async(cls, dataset_id: int, table_names: list[str], db_session: Session):
        """
        异步训练数据集，支持进度更新和中断控制
        
        流程：
        - Step 0-10%: 初始化、检查数据库连接、提取 DDL
        - Step 10-40%: 训练 DDL 到 Vanna
        - Step 40-80%: 训练文档/业务术语
        - Step 80-100%: 生成示例 SQLQA 对并训练
        
        Args:
            dataset_id: 数据集ID
            table_names: 要训练的表名列表
            db_session: 数据库会话
        """
        logger.info(f"Starting training for dataset {dataset_id} with tables: {table_names}")

        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.error(f"Dataset {dataset_id} not found")
            return

        try:
            # === Step 0: 初始化 (0%) ===
            dataset.status = "training"
            dataset.process_rate = 0
            dataset.error_msg = None
            db_session.commit()

            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 0, "训练启动")

            # === Step 1: 检查数据源并提取 DDL (0-10%) ===
            # 判断是 DuckDB 数据集还是传统数据源
            is_duckdb = dataset.duckdb_path is not None
            
            # 用于记录DDL提取结果
            ddls = []
            failed_tables = []  # 记录失败的表名
            
            if is_duckdb:
                cls._checkpoint_and_check_interrupt(db_session, dataset_id, 5, "检查 DuckDB 数据库")
                
                # 从 DuckDB 提取 DDLs
                for i, table_name in enumerate(table_names):
                    try:
                        ddl = DuckDBService.get_table_ddl(dataset.duckdb_path, table_name)
                        ddls.append((table_name, ddl))
                        
                        progress = 5 + int((i + 1) / len(table_names) * 5)
                        cls._checkpoint_and_check_interrupt(
                            db_session, dataset_id, progress,
                            f"提取表 DDL: {table_name} ({i+1}/{len(table_names)})"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get DDL for {table_name}: {e}")
                        failed_tables.append(f"{table_name} ({str(e)[:50]})")
            else:
                # 传统数据源
                datasource = dataset.datasource
                if not datasource:
                    raise ValueError("DataSource associated with dataset not found")

                cls._checkpoint_and_check_interrupt(db_session, dataset_id, 5, "检查数据源连接")

                # 提取 DDLs
                for i, table_name in enumerate(table_names):
                    try:
                        ddl = DBInspector.get_table_ddl(datasource, table_name)
                        ddls.append((table_name, ddl))

                        # 每处理一个表，更新一次进度
                        progress = 5 + int((i + 1) / len(table_names) * 5)
                        cls._checkpoint_and_check_interrupt(
                            db_session, dataset_id, progress,
                            f"提取表 DDL: {table_name} ({i+1}/{len(table_names)})"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get DDL for {table_name}: {e}")
                        failed_tables.append(f"{table_name} ({str(e)[:50]})")
                        # 继续处理其他表

            if not ddls:
                raise ValueError("没有成功提取任何表的 DDL")
            
            # 如果有部分表失败，记录到 error_msg
            if failed_tables:
                dataset.error_msg = f"部分表DDL提取失败: {', '.join(failed_tables)}"
                db_session.commit()

            # === Step 2: 初始化 Vanna 实例 (10%) ===
            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 10, "初始化 Vanna 实例")

            # 使用 Legacy API 进行训练
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            
            # 【重要】清理旧的训练数据，防止重复叠加
            # 注意：由于现在使用了基于内容的哈希 ID，重复训练相同内容不再是问题，
            # 但如果表结构发生了变化，旧的 DDL 仍然会保留。
            # 理想情况下，我们应该清理与该数据集相关的所有旧数据。
            # 但目前 PGVector 实现不支持按 metadata 批量删除（需要遍历）。
            # 鉴于我们已实现了幂等 ID，这里暂时依赖 ID 去重机制。
            # 如果需要彻底重置，建议在 VannaLegacyPGVector 中实现 reset_collection()
            
            # === Step 3: 训练 DDL (10-40%) ===
            for i, (table_name, ddl) in enumerate(ddls):
                if ddl:
                    vn.train(ddl=ddl)

                    # 更新进度
                    progress = 10 + int((i + 1) / len(ddls) * 30)
                    cls._checkpoint_and_check_interrupt(
                        db_session, dataset_id, progress,
                        f"训练 DDL: {table_name} ({i+1}/{len(ddls)})"
                    )

            # === Step 4: 训练文档/业务术语 (40-80%) ===
            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 40, "开始训练业务术语")

            # 获取并训练业务术语
            business_terms = db_session.query(BusinessTerm).filter(
                BusinessTerm.dataset_id == dataset_id
            ).all()

            if business_terms:
                for i, term in enumerate(business_terms):
                    doc_content = f"业务术语: {term.term}\n定义: {term.definition}"
                    vn.train(documentation=doc_content)

                    progress = 40 + int((i + 1) / len(business_terms) * 20)
                    cls._checkpoint_and_check_interrupt(
                        db_session, dataset_id, progress,
                        f"训练业务术语: {term.term} ({i+1}/{len(business_terms)})"
                    )
            else:
                cls._checkpoint_and_check_interrupt(db_session, dataset_id, 60, "无业务术语，跳过")

            # 训练表关系文档
            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 70, "生成表关系文档")

            # 生成表关系描述
            table_relationships_doc = f"""数据库表结构：
本数据集包含以下表：{', '.join([name for name, _ in ddls])}

请根据表名和字段名生成 SQL 查询。
"""
            vn.train(documentation=table_relationships_doc)
            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 80, "表关系文档训练完成")

            # === Step 5: 生成示例 SQLQA 对 (80-100%) ===
            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 85, "生成示例 SQL 查询")

            # 为主要表生成基本查询示例
            example_queries = []
            for table_name, ddl in ddls[:3]:  # 只为前3个表生成示例
                example_queries.append((
                    f"查询 {table_name} 表的所有数据",
                    f"SELECT * FROM {table_name} LIMIT 100"
                ))
                example_queries.append((
                    f"统计 {table_name} 表的总数",
                    f"SELECT COUNT(*) as total FROM {table_name}"
                ))
                
                # 根据表结构生成针对性示例
                # 提取列名（从DDL中简单解析）
                try:
                    # 匹配列定义（简化版本）
                    import re
                    column_pattern = r'^\s*`?(\w+)`?\s+\w+'
                    columns = []
                    for line in ddl.split('\n'):
                        match = re.match(column_pattern, line.strip())
                        if match and match.group(1).upper() not in ['PRIMARY', 'KEY', 'CONSTRAINT', 'FOREIGN', 'INDEX']:
                            columns.append(match.group(1))
                    
                    # 如果有列，生成更多示例
                    if len(columns) >= 2:
                        # 第一个列作为示例
                        first_col = columns[0]
                        example_queries.append((
                            f"按{first_col}分组统计{table_name}",
                            f"SELECT {first_col}, COUNT(*) as count FROM {table_name} GROUP BY {first_col} LIMIT 100"
                        ))
                        
                        # 如果列名包含常见模式，添加相应示例
                        for col in columns:
                            col_lower = col.lower()
                            # 日期相关
                            if 'date' in col_lower or 'time' in col_lower:
                                example_queries.append((
                                    f"按{col}排序查看{table_name}最新记录",
                                    f"SELECT * FROM {table_name} ORDER BY {col} DESC LIMIT 10"
                                ))
                                break
                            # 金额/数量相关
                            elif 'amount' in col_lower or 'quantity' in col_lower or 'price' in col_lower or 'total' in col_lower:
                                example_queries.append((
                                    f"查询{table_name}中{col}最大的记录",
                                    f"SELECT * FROM {table_name} ORDER BY {col} DESC LIMIT 10"
                                ))
                                break
                except Exception as parse_err:
                    logger.debug(f"Failed to parse DDL for {table_name}: {parse_err}")

            for i, (question, sql) in enumerate(example_queries):
                vn.train(question=question, sql=sql)

                progress = 85 + int((i + 1) / len(example_queries) * 15)
                cls._checkpoint_and_check_interrupt(
                    db_session, dataset_id, progress,
                    f"训练示例查询 ({i+1}/{len(example_queries)})"
                )

            # === 完成 (100%) ===
            dataset.status = "completed"
            dataset.process_rate = 100
            dataset.last_train_at = datetime.utcnow()
            db_session.commit()

            cls._checkpoint_and_check_interrupt(db_session, dataset_id, 100, "训练完成")

            logger.info(f"Training completed successfully for dataset {dataset_id}")

            # 清理缓存
            cleared = await VannaCacheService.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training dataset {dataset_id}")

        except TrainingStoppedException as e:
            # 被用户中断
            logger.warning(f"Training stopped by user for dataset {dataset_id}: {e}")
            dataset.error_msg = str(e)
            db_session.commit()

            # 记录中断日志
            training_log = TrainingLog(
                dataset_id=dataset_id,
                content=f"[{dataset.process_rate}%] 训练被用户中断"
            )
            db_session.add(training_log)
            db_session.commit()

        except Exception as e:
            # 训练失败
            logger.error(f"Training failed for dataset {dataset_id}: {e}", exc_info=True)
            dataset.status = "failed"
            dataset.error_msg = str(e)
            db_session.commit()

            # 记录错误日志
            training_log = TrainingLog(
                dataset_id=dataset_id,
                content=f"[{dataset.process_rate}%] 训练失败: {str(e)[:200]}"
            )
            db_session.add(training_log)
            db_session.commit()

    @classmethod
    async def train_term_async(cls, dataset_id: int, term: str, definition: str):
        """
        异步训练业务术语
        """
        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            doc_content = f"业务术语: {term}\n定义: {definition}"
            vn.train(documentation=doc_content)

            logger.info(f"Successfully trained business term '{term}' for dataset {dataset_id}")

            # 清理缓存
            cleared = await VannaCacheService.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training term '{term}'")

        except Exception as e:
            logger.error(f"Failed to train business term '{term}': {e}")
            raise ValueError(f"训练业务术语失败: {str(e)}")

    @classmethod
    def train_term(cls, dataset_id: int, term: str, definition: str, db_session: Session):
        """
        Train a business term by adding it to Vanna's documentation memory.
        Uses Legacy API for consistency with existing training approach.
        """
        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            doc_content = f"业务术语: {term}\n定义: {definition}"
            vn.train(documentation=doc_content)

            logger.info(f"Successfully trained business term '{term}' for dataset {dataset_id}")

            # 注意：这里是同步方法，无法直接调用异步缓存清理
            # 缓存清理应由调用方在异步上下文中处理

        except Exception as e:
            logger.error(f"Failed to train business term '{term}': {e}")
            raise ValueError(f"训练业务术语失败: {str(e)}")

    @classmethod
    async def train_relationships_async(cls, dataset_id: int, relationships: list[str]):
        """
        异步训练表关系
        """
        if not relationships:
            logger.info(f"No relationships to train for dataset {dataset_id}")
            return

        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)

            logger.info(f"Training {len(relationships)} relationships for dataset {dataset_id}")

            for i, rel_desc in enumerate(relationships, 1):
                doc_content = f"表关系: {rel_desc}"
                vn.train(documentation=doc_content)
                logger.debug(f"Trained relationship {i}/{len(relationships)}: {rel_desc[:80]}...")

            logger.info(f"Successfully trained {len(relationships)} relationships for dataset {dataset_id}")

            # 清理缓存
            cleared = await VannaCacheService.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training relationships")

        except Exception as e:
            logger.error(f"Failed to train relationships: {e}")
            raise ValueError(f"训练表关系失败: {str(e)}")

    @classmethod
    def train_relationships(cls, dataset_id: int, relationships: list[str], db_session: Session):
        """
        Train table relationships by adding them to Vanna's documentation memory.
        This enhances Vanna's ability to generate correct JOIN queries.
        """
        if not relationships:
            logger.info(f"No relationships to train for dataset {dataset_id}")
            return

        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)

            logger.info(f"Training {len(relationships)} relationships for dataset {dataset_id}")

            for i, rel_desc in enumerate(relationships, 1):
                doc_content = f"表关系: {rel_desc}"
                vn.train(documentation=doc_content)
                logger.debug(f"Trained relationship {i}/{len(relationships)}: {rel_desc[:80]}...")

            logger.info(f"Successfully trained {len(relationships)} relationships for dataset {dataset_id}")

        except Exception as e:
            logger.error(f"Failed to train relationships: {e}")
            raise ValueError(f"训练表关系失败: {str(e)}")

    @classmethod
    async def train_qa_async(cls, dataset_id: int, question: str, sql: str):
        """
        异步训练问答对
        """
        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            vn.train(question=question, sql=sql)

            logger.info(f"Successfully trained Q-A pair for dataset {dataset_id}: '{question[:50]}...'")

            # 清理缓存
            cleared = await VannaCacheService.clear_cache(dataset_id)
            if cleared >= 0:
                logger.info(f"Cleared {cleared} cached queries after training Q-A pair")

        except Exception as e:
            logger.error(f"Failed to train Q-A pair for dataset {dataset_id}: {e}")
            raise ValueError(f"训练问答对失败: {str(e)}")

    @classmethod
    def train_qa(cls, dataset_id: int, question: str, sql: str, db_session: Session):
        """
        Train a successful question-SQL pair from user feedback.
        This helps AI learn from correct examples and improve future responses.
        """
        try:
            vn = VannaInstanceManager.get_legacy_vanna(dataset_id)
            vn.train(question=question, sql=sql)

            logger.info(f"Successfully trained Q-A pair for dataset {dataset_id}: '{question[:50]}...'")

        except Exception as e:
            logger.error(f"Failed to train Q-A pair for dataset {dataset_id}: {e}")
            raise ValueError(f"训练问答对失败: {str(e)}")
