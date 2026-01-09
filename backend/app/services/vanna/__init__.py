"""
Vanna 服务模块

提供 SQL 生成、训练、缓存等核心功能的模块化服务。
"""

from app.services.vanna.base import (
    VannaLegacyPGVector,
    SimpleUserResolver,
    TrainingStoppedException,
)

# Backward compatibility alias
VannaLegacy = VannaLegacyPGVector
from app.services.vanna.instance_manager import VannaInstanceManager
from app.services.vanna.cache_service import VannaCacheService
from app.services.vanna.training_service import VannaTrainingService
from app.services.vanna.sql_generator import VannaSqlGenerator
from app.services.vanna.analyst_service import VannaAnalystService
from app.services.vanna.training_data_service import VannaTrainingDataService
from app.services.vanna.agent_manager import VannaAgentManager
from app.services.vanna.facade import VannaManager

__all__ = [
    # 外观类（推荐使用）
    "VannaManager",
    "VannaAgentManager",
    # 基础类
    "VannaLegacy",  # Alias for VannaLegacyPGVector (backward compatibility)
    "VannaLegacyPGVector",
    "SimpleUserResolver",
    "TrainingStoppedException",
    # 服务类（高级用法）
    "VannaInstanceManager",
    "VannaCacheService",
    "VannaTrainingService",
    "VannaSqlGenerator",
    "VannaAnalystService",
    "VannaTrainingDataService",
]
