# VannaManager 完整重构计划

## 重构目标

1. 将 2664 行的 `vanna_manager.py` 拆分为职责单一的服务类
2. 消除 `nest_asyncio` hack，统一异步模式
3. 添加 Legacy/Agent 模式切换配置

---

## 职责分析

### 当前 VannaManager 包含的方法（按职责分组）

| 职责 | 方法 | 行数估算 |
|------|------|----------|
| **实例管理** | `get_legacy_vanna`, `get_agent`, `_get_global_chroma_client`, `delete_collection` | ~200 |
| **缓存** | `clear_cache`, `clear_cache_async` | ~70 |
| **训练** | `train_dataset`, `train_dataset_async`, `train_term`, `train_relationships`, `train_qa`, `_checkpoint_and_check_interrupt` | ~600 |
| **SQL 生成** | `generate_result` (含缓存逻辑、执行、错误处理) | ~600 |
| **业务分析** | `generate_summary`, `generate_data_insight`, `analyze_relationships` | ~400 |
| **工具方法** | `_infer_chart_type`, `_serialize_dataframe`, `_clean_sql`, `_is_valid_sql`, `_ensure_clean_sql`, `_extract_intermediate_sql`, `_is_clarification_request`, `_remove_intermediate_marker` | ~300 |
| **训练数据管理** | `get_training_data`, `remove_training_data` | ~200 |

---

## 新文件结构

```
backend/app/services/
├── vanna/
│   ├── __init__.py              # 导出公共接口
│   ├── base.py                  # VannaLegacy, VannaLegacyPGVector 类
│   ├── instance_manager.py      # Vanna 实例管理 (单例、缓存)
│   ├── training_service.py      # 训练服务
│   ├── sql_generator.py         # SQL 生成 + 执行
│   ├── cache_service.py         # Redis 缓存管理 (纯异步)
│   ├── analyst_service.py       # 业务分析 (summary, insight)
│   ├── training_data_service.py # 训练数据 CRUD
│   └── utils.py                 # 工具方法
├── vanna_tools.py               # (保留) Agent 工具
├── vanna_enhancer.py            # (保留) 上下文增强器
└── vanna_manager.py             # (保留) 向后兼容的 Facade
```

---

## 详细实现计划

### Phase 1: 创建基础结构

**Step 1.1**: 创建 `vanna/` 目录和 `__init__.py`

**Step 1.2**: 创建 `vanna/base.py`
- 移动 `VannaLegacy` 类 (L50-170)
- 移动 `VannaLegacyPGVector` 类 (L156-370)
- 移动 `SimpleUserResolver` 类 (L375-377)
- 移动 `TrainingStoppedException` 类 (L45-47)

**Step 1.3**: 创建 `vanna/utils.py`
- 移动 `_infer_chart_type` (L1762-1796)
- 移动 `_serialize_dataframe` (L1798-1842)
- 移动 `_clean_sql` (L2015-2034)
- 移动 `_is_valid_sql` (L1844-1873)
- 移动 `_ensure_clean_sql` (L1875-1903)
- 移动 `_extract_intermediate_sql` (L1905-1972)
- 移动 `_is_clarification_request` (L1974-2013)
- 移动 `_remove_intermediate_marker` (L1824-1842)

### Phase 2: 拆分核心服务

**Step 2.1**: 创建 `vanna/instance_manager.py`
```python
class VannaInstanceManager:
    """Vanna 实例生命周期管理"""
    _legacy_instances: dict = {}
    _agent_instances: dict = {}
    _global_chroma_client = None

    @classmethod
    def get_legacy_vanna(cls, dataset_id: int) -> VannaLegacy: ...
    @classmethod
    def get_agent(cls, dataset_id: int) -> Agent: ...
    @classmethod
    def delete_collection(cls, dataset_id: int) -> bool: ...
    @classmethod
    def clear_instance_cache(cls, dataset_id: int = None): ...
```

**Step 2.2**: 创建 `vanna/cache_service.py`
```python
class VannaCacheService:
    """纯异步缓存服务 (消除 nest_asyncio)"""

    @classmethod
    async def clear_cache(cls, dataset_id: int) -> int: ...

    @classmethod
    async def get_cached_sql(cls, dataset_id: int, question: str) -> str | None: ...

    @classmethod
    async def cache_sql(cls, dataset_id: int, question: str, sql: str) -> bool: ...
```

**Step 2.3**: 创建 `vanna/training_service.py`
```python
class VannaTrainingService:
    """训练相关操作"""

    @classmethod
    async def train_dataset(cls, dataset_id: int, table_names: list, db_session: Session): ...

    @classmethod
    def train_term(cls, dataset_id: int, term: str, definition: str, db_session: Session): ...

    @classmethod
    def train_relationships(cls, dataset_id: int, relationships: list, db_session: Session): ...

    @classmethod
    def train_qa(cls, dataset_id: int, question: str, sql: str, db_session: Session): ...
```

**Step 2.4**: 创建 `vanna/sql_generator.py`
```python
class VannaSqlGenerator:
    """SQL 生成和执行"""

    @classmethod
    async def generate_result(
        cls,
        dataset_id: int,
        question: str,
        db_session: Session,
        use_cache: bool = True
    ) -> dict: ...
```

**Step 2.5**: 创建 `vanna/analyst_service.py`
```python
class VannaAnalystService:
    """业务分析服务"""

    @classmethod
    def generate_summary(cls, question: str, df: pd.DataFrame, dataset_id: int) -> str: ...

    @classmethod
    def generate_data_insight(cls, question: str, sql: str, df: pd.DataFrame, dataset_id: int) -> str: ...

    @classmethod
    def analyze_relationships(cls, dataset_id: int, table_names: list, db_session: Session) -> dict: ...
```

**Step 2.6**: 创建 `vanna/training_data_service.py`
```python
class VannaTrainingDataService:
    """训练数据 CRUD"""

    @classmethod
    def get_training_data(cls, dataset_id: int, page: int, page_size: int, type_filter: str) -> dict: ...

    @classmethod
    def remove_training_data(cls, dataset_id: int, training_data_id: str) -> bool: ...
```

### Phase 3: 更新配置和端点

**Step 3.1**: 添加模式切换配置到 `config.py`
```python
# Vanna API 模式
VANNA_API_MODE: str = os.getenv("VANNA_API_MODE", "legacy")  # "legacy" | "agent"
```

**Step 3.2**: 直接更新 API 端点导入（不保留 Facade）

`chat.py`:
```python
from app.services.vanna import VannaSqlGenerator, VannaAnalystService
from app.services.vanna_manager import VannaAgentManager  # Agent 保留在原位置

# /chat 端点
if settings.VANNA_API_MODE == "agent":
    result = await VannaAgentManager.chat_simple(...)
else:
    result = await VannaSqlGenerator.generate_result(...)
```

`dataset.py`:
```python
from app.services.vanna import (
    VannaInstanceManager,
    VannaTrainingService,
    VannaCacheService,
    VannaTrainingDataService,
    VannaAnalystService
)
```

### Phase 4: 删除旧代码

**Step 4.1**: 删除 `vanna_manager.py` 中已迁移的代码
- 保留 `VannaAgentManager` 类
- 删除 `VannaManager` 类
- 删除 `VannaLegacy`, `VannaLegacyPGVector` 类
- 删除辅助类和工具方法

**Step 4.2**: 重命名文件
- `vanna_manager.py` → `vanna_agent.py` (只包含 VannaAgentManager)

---

## 关键修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/vanna/__init__.py` | 新建 | 公共接口导出 |
| `services/vanna/base.py` | 新建 | VannaLegacy 类 |
| `services/vanna/utils.py` | 新建 | 工具方法 |
| `services/vanna/instance_manager.py` | 新建 | 实例管理 |
| `services/vanna/cache_service.py` | 新建 | 缓存服务 (纯异步) |
| `services/vanna/training_service.py` | 新建 | 训练服务 |
| `services/vanna/sql_generator.py` | 新建 | SQL 生成 |
| `services/vanna/analyst_service.py` | 新建 | 业务分析 |
| `services/vanna/training_data_service.py` | 新建 | 训练数据 CRUD |
| `services/vanna_manager.py` | 重命名 | → `vanna_agent.py`，只保留 VannaAgentManager |
| `core/config.py` | 修改 | 添加 VANNA_API_MODE |
| `api/v1/endpoints/chat.py` | 修改 | 更新导入，添加模式切换 |
| `api/v1/endpoints/dataset.py` | 修改 | 更新导入 |

---

## 风险和注意事项

1. **破坏性变更**: 不保留 Facade，所有调用方需更新导入
2. **异步一致性**: `cache_service.py` 只提供异步方法，调用方需使用 `await`
3. **循环导入**: 注意 `vanna/` 包内部的依赖关系，使用延迟导入避免循环
4. **同步方法处理**: `train_term`, `train_qa` 等同步方法中调用缓存清理需要改为异步

