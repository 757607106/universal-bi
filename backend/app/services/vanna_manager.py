"""
VannaManager 兼容性模块

此模块从新的模块化服务中重新导出类，保持向后兼容性。
新代码应直接从 app.services.vanna 导入。

重构后的模块结构：
- app.services.vanna.base          - VannaLegacy, VannaLegacyPGVector 等基础类
- app.services.vanna.instance_manager - 实例生命周期管理
- app.services.vanna.cache_service    - Redis 缓存服务
- app.services.vanna.training_service - 训练相关功能
- app.services.vanna.sql_generator    - SQL 生成和执行
- app.services.vanna.analyst_service  - 业务分析功能
- app.services.vanna.training_data_service - 训练数据 CRUD
- app.services.vanna.agent_manager    - Vanna 2.0 Agent API
- app.services.vanna.facade          - VannaManager 外观类
"""

# 从新模块导入所有公开类
from app.services.vanna import (
    # 主要使用的外观类
    VannaManager,
    VannaAgentManager,
    # 基础类（可能被直接使用）
    VannaLegacy,
    VannaLegacyPGVector,
    SimpleUserResolver,
    TrainingStoppedException,
    # 服务类（高级用法）
    VannaInstanceManager,
    VannaCacheService,
    VannaTrainingService,
    VannaSqlGenerator,
    VannaAnalystService,
    VannaTrainingDataService,
)

__all__ = [
    "VannaManager",
    "VannaAgentManager",
    "VannaLegacy",
    "VannaLegacyPGVector",
    "SimpleUserResolver",
    "TrainingStoppedException",
    "VannaInstanceManager",
    "VannaCacheService",
    "VannaTrainingService",
    "VannaSqlGenerator",
    "VannaAnalystService",
    "VannaTrainingDataService",
]
