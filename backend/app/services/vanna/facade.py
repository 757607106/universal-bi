"""
VannaManager 外观类

提供统一的 API 接口，代理到各个拆分后的服务模块。
保持与原有 vanna_manager.py 中 VannaManager 类相同的接口，确保向后兼容。
"""

from sqlalchemy.orm import Session

from app.services.vanna.instance_manager import VannaInstanceManager
from app.services.vanna.cache_service import VannaCacheService
from app.services.vanna.training_service import VannaTrainingService
from app.services.vanna.sql_generator import VannaSqlGenerator
from app.services.vanna.analyst_service import VannaAnalystService
from app.services.vanna.training_data_service import VannaTrainingDataService


class VannaManager:
    """
    Vanna 服务外观类

    提供统一的 API 接口，将请求代理到各个专门的服务类。
    保持原有接口兼容性，方便平滑迁移。
    """

    # ========== 实例管理 ==========

    @classmethod
    def get_legacy_vanna(cls, dataset_id: int):
        """获取 Legacy Vanna 实例"""
        return VannaInstanceManager.get_legacy_vanna(dataset_id)

    @classmethod
    def get_agent(cls, dataset_id: int):
        """获取 Vanna Agent 实例"""
        return VannaInstanceManager.get_agent(dataset_id)

    @classmethod
    def delete_collection(cls, dataset_id: int) -> bool:
        """删除数据集的 Collection"""
        return VannaInstanceManager.delete_collection(dataset_id)

    @classmethod
    def clear_instance_cache(cls, dataset_id: int = None):
        """清除实例缓存"""
        VannaInstanceManager.clear_instance_cache(dataset_id)

    # ========== 缓存服务 ==========

    @classmethod
    async def clear_cache_async(cls, dataset_id: int) -> int:
        """异步清除缓存"""
        return await VannaCacheService.clear_cache(dataset_id)

    @classmethod
    def clear_cache(cls, dataset_id: int) -> int:
        """
        同步清除缓存（兼容性方法）
        注意：建议使用 clear_cache_async
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(VannaCacheService.clear_cache(dataset_id))

    # ========== 训练服务 ==========

    @classmethod
    def train_dataset(cls, dataset_id: int, table_names: list[str], db_session: Session):
        """训练数据集"""
        VannaTrainingService.train_dataset(dataset_id, table_names, db_session)

    @classmethod
    async def train_dataset_async(cls, dataset_id: int, table_names: list[str], db_session: Session):
        """异步训练数据集"""
        await VannaTrainingService.train_dataset_async(dataset_id, table_names, db_session)

    @classmethod
    def train_term(cls, dataset_id: int, term: str, definition: str, db_session: Session):
        """训练业务术语"""
        VannaTrainingService.train_term(dataset_id, term, definition, db_session)

    @classmethod
    async def train_term_async(cls, dataset_id: int, term: str, definition: str):
        """异步训练业务术语"""
        await VannaTrainingService.train_term_async(dataset_id, term, definition)

    @classmethod
    def train_relationships(cls, dataset_id: int, relationships: list[str], db_session: Session):
        """训练表关系"""
        VannaTrainingService.train_relationships(dataset_id, relationships, db_session)

    @classmethod
    async def train_relationships_async(cls, dataset_id: int, relationships: list[str]):
        """异步训练表关系"""
        await VannaTrainingService.train_relationships_async(dataset_id, relationships)

    @classmethod
    def train_qa(cls, dataset_id: int, question: str, sql: str, db_session: Session):
        """训练问答对"""
        VannaTrainingService.train_qa(dataset_id, question, sql, db_session)

    @classmethod
    async def train_qa_async(cls, dataset_id: int, question: str, sql: str):
        """异步训练问答对"""
        await VannaTrainingService.train_qa_async(dataset_id, question, sql)

    # ========== SQL 生成服务 ==========

    @classmethod
    async def generate_result(cls, dataset_id: int, question: str, db_session: Session, use_cache: bool = True):
        """生成 SQL 并执行"""
        return await VannaSqlGenerator.generate_result(dataset_id, question, db_session, use_cache)

    # ========== 分析服务 ==========

    @classmethod
    def generate_summary(cls, question: str, df, dataset_id: int) -> str:
        """生成数据总结"""
        return VannaAnalystService.generate_summary(question, df, dataset_id)

    @classmethod
    def generate_data_insight(cls, question: str, sql: str, df, dataset_id: int) -> str:
        """生成业务洞察"""
        return VannaAnalystService.generate_data_insight(question, sql, df, dataset_id)

    @classmethod
    def analyze_relationships(cls, dataset_id: int, table_names: list[str], db_session: Session) -> dict:
        """分析表关系"""
        return VannaAnalystService.analyze_relationships(dataset_id, table_names, db_session)

    # ========== 训练数据服务 ==========

    @classmethod
    def get_training_data(cls, dataset_id: int, page: int = 1, page_size: int = 20, type_filter: str = None) -> dict:
        """获取训练数据"""
        return VannaTrainingDataService.get_training_data(dataset_id, page, page_size, type_filter)

    @classmethod
    def remove_training_data(cls, dataset_id: int, training_data_id: str) -> bool:
        """删除训练数据"""
        return VannaTrainingDataService.remove_training_data(dataset_id, training_data_id)

    @classmethod
    async def remove_training_data_async(cls, dataset_id: int, training_data_id: str) -> bool:
        """异步删除训练数据"""
        return await VannaTrainingDataService.remove_training_data_async(dataset_id, training_data_id)

    # ========== 建议问题生成 ==========

    @classmethod
    def generate_suggested_questions(cls, dataset_id: int, db_session: Session, limit: int = 5) -> list[str]:
        """生成建议问题"""
        return VannaAnalystService.generate_suggested_questions(dataset_id, db_session, limit)
