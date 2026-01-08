# Vanna AI 2.0 使用分析报告

## 一、当前实现架构概述

### 1.1 代码位置
- 核心文件：[backend/app/services/vanna_manager.py](backend/app/services/vanna_manager.py)

### 1.2 当前架构
你的项目同时导入了 **Vanna 2.0 Agent API** 和 **Vanna Legacy API**，但实际使用的是 **Legacy API**：

```python
# Vanna 2.0 Imports (导入但未真正使用)
from vanna.core import Agent, ToolRegistry, ToolContext
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory

# Legacy API (实际使用)
from vanna.legacy.openai import OpenAI_Chat
from vanna.legacy.chromadb import ChromaDB_VectorStore
```

---

## 二、发现的问题

### 2.1 ⚠️ 问题 1：Legacy API 初始化不符合官方规范

**当前代码** (`VannaLegacy.__init__`):
```python
class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None, chroma_client=None):
        self.config = config or {}
        # ... 手动设置大量属性 ...
        if config and 'api_base' in config:
            self.client = OpenAIClient(
                api_key=config.get('api_key'),
                base_url=config.get('api_base')  # ❌ Legacy 已废弃 api_base 参数
            )
```

**官方 Legacy OpenAI_Chat** (第 18-25 行):
```python
if "api_base" in config:
    raise Exception(
        "Passing api_base is now deprecated. Please pass an OpenAI client instead."
    )
```

**问题**：你绕过了官方的初始化逻辑，直接创建 OpenAI client 来支持 `api_base`，这样做虽然能工作，但：
- 跳过了父类 `VannaBase.__init__()` 的完整调用链
- `submit_prompt` 方法重写可能与父类行为不一致

---

### 2.2 ⚠️ 问题 2：ChromaDB Collection 命名不一致

**当前代码**：
```python
# 你的代码为每个 dataset 创建独立 collection 前缀
collection_name = f"vec_ds_{dataset_id}"  # 如: vec_ds_1

# 然后创建 3 个子 collection
self.ddl_collection = f"{collection_name}_ddl"           # vec_ds_1_ddl
self.sql_collection = f"{collection_name}_sql"           # vec_ds_1_sql
self.documentation_collection = f"{collection_name}_documentation"  # vec_ds_1_documentation
```

**官方 ChromaDB_VectorStore** (第 45-59 行):
```python
# 官方使用固定名称
self.documentation_collection = self.chroma_client.get_or_create_collection(name="documentation")
self.ddl_collection = self.chroma_client.get_or_create_collection(name="ddl")
self.sql_collection = self.chroma_client.get_or_create_collection(name="sql")
```

**问题**：你的多租户隔离方案是合理的，但与官方 API 行为不一致。这不是 bug，而是你为了支持多数据集隔离做的定制化。

---

### 2.3 ⚠️ 问题 3：Vanna 2.0 Agent 未被有效利用

**当前代码**：
```python
def get_agent(dataset_id: int):
    """Initialize and return a configured Vanna Agent instance (Vanna 2.0)."""
    agent = Agent(
        llm_service=llm_service,
        tool_registry=registry,  # ❌ 空的 registry，没有注册任何工具
        user_resolver=SimpleUserResolver(),
        agent_memory=agent_memory,
        llm_context_enhancer=enhancer
    )
    return agent
```

**问题**：
1. `get_agent()` 方法创建了 Agent 实例，但代码中 **从未调用** 它进行 SQL 生成
2. 所有 SQL 生成逻辑都走的是 `get_legacy_vanna()` 返回的 Legacy 实例
3. `ToolRegistry` 是空的，没有注册 SQL 执行等工具

---

### 2.4 ⚠️ 问题 4：自定义中间 SQL 检测逻辑与官方重复

**你的代码**：
```python
def _extract_intermediate_sql(response: str) -> str:
    """Extract intermediate SQL from LLM response..."""
    # 100+ 行自定义逻辑
```

**官方 VannaBase.generate_sql** (第 139-167 行):
```python
if "intermediate_sql" in llm_response:
    if allow_llm_to_see_data:
        intermediate_sql = self.extract_sql(llm_response)
        df = self.run_sql(intermediate_sql)
        # 自动执行并进行二次推理
```

**问题**：官方已经内置了 `intermediate_sql` 的处理逻辑，你的自定义实现是一种重复，虽然功能更强但增加了维护成本。

---

### 2.5 ⚠️ 问题 5：未利用 `allow_llm_to_see_data` 参数

**官方 API**：
```python
sql = vn.generate_sql(question, allow_llm_to_see_data=True)
```

**你的代码**：
```python
vn.allow_llm_to_see_data = True  # 仅设置属性，但没在 generate_sql 调用中传递
llm_response = vn.generate_sql(question + " (请用中文回答)")  # ❌ 缺少参数
```

**问题**：虽然设置了 `vn.allow_llm_to_see_data = True`，但这个属性不会自动生效，需要在调用 `generate_sql` 时显式传递。

---

## 三、优化建议

### 3.1 优化方案 A：完善 Legacy API 使用（低风险，推荐）

#### 修改 1：正确初始化 VannaLegacy

```python
class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None, chroma_client=None):
        # 1. 先调用 VannaBase 初始化
        from vanna.legacy.base import VannaBase
        VannaBase.__init__(self, config=config)

        # 2. 初始化 ChromaDB (使用传入的 client)
        if chroma_client is not None:
            self._init_chromadb_with_client(config, chroma_client)
        else:
            ChromaDB_VectorStore.__init__(self, config=config)

        # 3. 初始化 OpenAI client（传入自定义 client 而非 api_base）
        custom_client = OpenAIClient(
            api_key=config.get('api_key'),
            base_url=config.get('api_base')
        )
        OpenAI_Chat.__init__(self, client=custom_client, config=config)
```

#### 修改 2：正确使用 `allow_llm_to_see_data`

```python
# 在 generate_result 中
llm_response = vn.generate_sql(
    question + " (请用中文回答)",
    allow_llm_to_see_data=True  # ✅ 显式传递
)
```

#### 修改 3：利用官方内置的 intermediate_sql 处理

```python
# 可以删除或简化你的 _extract_intermediate_sql 方法
# 官方的 generate_sql 会自动处理 intermediate_sql
# 如果你想保留更多控制，可以扩展而非完全重写
```

---

### 3.2 优化方案 B：迁移到 Vanna 2.0 Agent API（中风险，更强大）

Vanna 2.0 Agent API 提供了更强大的能力：

```python
from vanna.core import Agent, ToolRegistry
from vanna.capabilities.sql_runner import SqlRunnerCapability

# 1. 注册 SQL 执行工具
registry = ToolRegistry()
registry.register(SqlRunnerCapability(
    connection_string=datasource.connection_string
))

# 2. 创建 Agent
agent = Agent(
    llm_service=llm_service,
    tool_registry=registry,
    agent_memory=agent_memory,
    llm_context_enhancer=DefaultLlmContextEnhancer(agent_memory)
)

# 3. 使用 Agent 进行对话
async for component in agent.send_message(request_context, question):
    # 处理 UI 组件
```

**优势**：
- 内置工具执行机制
- 流式响应支持
- 对话历史管理
- 可观测性/审计支持

---

### 3.3 优化方案 C：其他细节优化

#### C1. 使用更强的 Embedding Function

```python
from vanna.integrations.chromadb import create_sentence_transformer_embedding_function

# 使用 SentenceTransformer 替代默认的 Embedding
ef = create_sentence_transformer_embedding_function(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vn = VannaLegacy(config={
    'embedding_function': ef,
    ...
})
```

#### C2. 增加 n_results 动态调整

```python
# 根据问题复杂度动态调整检索数量
def get_optimal_n_results(question: str) -> int:
    if len(question) > 100 or '和' in question or 'join' in question.lower():
        return 15  # 复杂问题需要更多上下文
    return 10
```

#### C3. 训练数据质量优化

```python
# 在训练 QA 对时，验证 SQL 的可执行性
def train_qa(self, dataset_id, question, sql, db_session):
    # 先验证 SQL
    try:
        engine = DBInspector.get_engine(datasource)
        pd.read_sql(sql + " LIMIT 1", engine)  # 验证可执行
    except Exception as e:
        logger.warning(f"Invalid SQL, skipping training: {e}")
        return

    vn.train(question=question, sql=sql)
```

---

## 四、优先级建议

| 优先级 | 优化项 | 风险 | 收益 |
|--------|--------|------|------|
| P0 | 修复 `allow_llm_to_see_data` 参数传递 | 低 | 高 - 启用官方 intermediate_sql 支持 |
| P1 | 完善 Legacy API 初始化 | 低 | 中 - 代码更规范 |
| P2 | 删除冗余的 Agent 代码 | 低 | 低 - 减少混淆 |
| P3 | 考虑迁移到 Agent API | 中 | 高 - 获得更强能力 |
| P4 | 使用更强的 Embedding | 低 | 中 - 提升检索质量 |

---

---

## 五、Vanna 2.0 Agent API 迁移方案

基于你的选择，以下是完整的迁移方案。

### 5.1 Agent API 架构对比

| 特性 | Legacy API (当前) | Agent API (目标) |
|------|------------------|-----------------|
| SQL 生成 | `vn.generate_sql()` | Tool + LLM 自动调用 |
| 对话历史 | 手动管理 | `ConversationStore` 自动管理 |
| 流式响应 | 不支持 | `AsyncGenerator[UiComponent]` |
| 工具执行 | 无 | `ToolRegistry` + `Tool` 体系 |
| 上下文增强 | 手动构建 prompt | `LlmContextEnhancer` 自动注入 |
| 可观测性 | 无 | `ObservabilityProvider` 内置 |
| 错误恢复 | 手动处理 | `ErrorRecoveryStrategy` |

### 5.2 迁移步骤

#### 步骤 1：创建自定义 Tools

需要创建以下工具来替代 Legacy API 的功能：

```python
# backend/app/services/vanna_tools.py

from vanna.core.tool import Tool, ToolContext, ToolResult, ToolSchema
from vanna.components import UiComponent, SimpleTextComponent, RichTextComponent

class GenerateSqlTool(Tool):
    """基于用户问题生成 SQL 查询"""

    def __init__(self, vanna_legacy, datasource):
        self.vn = vanna_legacy
        self.datasource = datasource

    async def get_schema(self, user) -> ToolSchema:
        return ToolSchema(
            name="generate_sql",
            description="根据自然语言问题生成 SQL 查询",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户的自然语言问题"
                    }
                },
                "required": ["question"]
            }
        )

    async def execute(self, args: dict, context: ToolContext) -> ToolResult:
        question = args.get("question", "")
        try:
            sql = self.vn.generate_sql(question, allow_llm_to_see_data=True)
            return ToolResult(
                success=True,
                result_for_llm=f"生成的 SQL:\n```sql\n{sql}\n```",
                ui_component=UiComponent(
                    rich_component=RichTextComponent(
                        content=f"```sql\n{sql}\n```",
                        markdown=True
                    ),
                    simple_component=SimpleTextComponent(text=sql)
                )
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ExecuteSqlTool(Tool):
    """执行 SQL 查询并返回结果"""

    def __init__(self, datasource):
        self.datasource = datasource

    async def get_schema(self, user) -> ToolSchema:
        return ToolSchema(
            name="execute_sql",
            description="执行 SQL 查询并返回结果",
            parameters={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "要执行的 SQL 查询"}
                },
                "required": ["sql"]
            }
        )

    async def execute(self, args: dict, context: ToolContext) -> ToolResult:
        sql = args.get("sql", "")
        try:
            engine = DBInspector.get_engine(self.datasource)
            df = pd.read_sql(sql, engine)
            result_json = df.head(100).to_json(orient="records", force_ascii=False)
            return ToolResult(
                success=True,
                result_for_llm=f"查询返回 {len(df)} 行数据:\n{result_json}",
                ui_component=None  # 可以创建 DataTableComponent
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

#### 步骤 2：创建自定义 LlmContextEnhancer

```python
# backend/app/services/vanna_enhancer.py

from vanna.core.enhancer import LlmContextEnhancer

class VannaContextEnhancer(LlmContextEnhancer):
    """增强 LLM 上下文，注入 DDL、文档和相似问答"""

    def __init__(self, agent_memory, vanna_legacy):
        self.agent_memory = agent_memory
        self.vn = vanna_legacy

    async def enhance_system_prompt(
        self, system_prompt: str, user_message: str, user
    ) -> str:
        # 获取相关的 DDL
        ddl_list = self.vn.get_related_ddl(user_message)

        # 获取相关文档
        doc_list = self.vn.get_related_documentation(user_message)

        # 获取相似问答对
        qa_list = self.vn.get_similar_question_sql(user_message)

        # 构建增强的 system prompt
        enhanced_prompt = system_prompt

        if ddl_list:
            enhanced_prompt += "\n\n## 相关数据库表结构\n\n"
            for ddl in ddl_list[:5]:  # 限制数量
                enhanced_prompt += f"```sql\n{ddl}\n```\n"

        if doc_list:
            enhanced_prompt += "\n\n## 业务文档\n\n"
            for doc in doc_list[:3]:
                enhanced_prompt += f"- {doc}\n"

        if qa_list:
            enhanced_prompt += "\n\n## 类似问答示例\n\n"
            for qa in qa_list[:5]:
                if isinstance(qa, dict) and 'question' in qa and 'sql' in qa:
                    enhanced_prompt += f"问: {qa['question']}\n答:\n```sql\n{qa['sql']}\n```\n\n"

        return enhanced_prompt

    async def enhance_user_messages(self, messages, user):
        return messages  # 默认不修改
```

#### 步骤 3：重构 VannaManager

```python
# backend/app/services/vanna_manager.py (重构后)

from vanna.core import Agent, ToolRegistry
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core.user.resolver import UserResolver
from vanna.core.user.request_context import RequestContext

class VannaAgentManager:
    """Vanna 2.0 Agent 管理器"""

    _instances: Dict[int, Agent] = {}

    @classmethod
    def get_agent(cls, dataset_id: int, datasource: DataSource) -> Agent:
        if dataset_id not in cls._instances:
            cls._instances[dataset_id] = cls._create_agent(dataset_id, datasource)
        return cls._instances[dataset_id]

    @classmethod
    def _create_agent(cls, dataset_id: int, datasource: DataSource) -> Agent:
        # 1. 创建 LLM 服务
        llm_service = OpenAILlmService(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )

        # 2. 创建 Agent Memory (ChromaDB)
        agent_memory = ChromaAgentMemory(
            persist_directory=f"./chroma_data/agent_{dataset_id}",
            collection_name=f"agent_memory_{dataset_id}"
        )

        # 3. 创建 Legacy Vanna 实例 (用于现有训练数据)
        vanna_legacy = cls._get_legacy_vanna(dataset_id)

        # 4. 注册工具
        registry = ToolRegistry()
        registry.register(GenerateSqlTool(vanna_legacy, datasource))
        registry.register(ExecuteSqlTool(datasource))

        # 5. 创建 Context Enhancer
        enhancer = VannaContextEnhancer(agent_memory, vanna_legacy)

        # 6. 创建 Agent
        agent = Agent(
            llm_service=llm_service,
            tool_registry=registry,
            user_resolver=SimpleUserResolver(),
            agent_memory=agent_memory,
            llm_context_enhancer=enhancer,
            config=AgentConfig(
                max_tool_iterations=10,
                stream_responses=True,
                auto_save_conversations=True
            )
        )

        return agent

    @classmethod
    async def chat(
        cls,
        dataset_id: int,
        question: str,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[UiComponent, None]:
        """使用 Agent 进行对话"""
        agent = cls.get_agent(dataset_id, datasource)

        request_context = RequestContext(
            user_id=user_id,
            metadata={"dataset_id": dataset_id}
        )

        async for component in agent.send_message(
            request_context,
            question,
            conversation_id=conversation_id
        ):
            yield component
```

#### 步骤 4：更新 API 端点

```python
# backend/app/api/v1/endpoints/chat.py (更新)

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

@router.post("/agent-chat")
async def agent_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """使用 Vanna 2.0 Agent 进行对话 (流式响应)"""

    async def generate():
        async for component in VannaAgentManager.chat(
            dataset_id=request.dataset_id,
            question=request.question,
            user_id=str(current_user.id),
            conversation_id=request.conversation_id
        ):
            # 序列化 UiComponent
            yield json.dumps({
                "type": component.__class__.__name__,
                "data": component.to_dict()
            }) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
```

### 5.3 关键修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| [backend/app/services/vanna_manager.py](backend/app/services/vanna_manager.py) | 添加 `VannaAgentManager` 类，保留 Legacy 兼容 |
| [backend/app/services/vanna_tools.py](backend/app/services/vanna_tools.py) | 新建，实现 `GenerateSqlTool`、`ExecuteSqlTool` |
| [backend/app/services/vanna_enhancer.py](backend/app/services/vanna_enhancer.py) | 新建，实现 `VannaContextEnhancer` |
| [backend/app/api/v1/endpoints/chat.py](backend/app/api/v1/endpoints/chat.py) | 添加 `/agent-chat` 流式端点 |

### 5.4 提升 SQL 生成质量的附加优化

针对你提到的 SQL 生成不准确和检索问题，可以在迁移过程中同步优化：

#### A. 使用更强的 Embedding 模型

```python
from vanna.integrations.chromadb import create_sentence_transformer_embedding_function

# 使用更强的多语言模型 (对中文支持更好)
ef = create_sentence_transformer_embedding_function(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

#### B. 增加检索结果数量

```python
# 在 VannaLegacy 配置中
config = {
    'n_results_sql': 15,  # 增加到 15
    'n_results_ddl': 10,
    'n_results_documentation': 10,
}
```

#### C. 添加 SQL 验证

```python
class ExecuteSqlTool(Tool):
    async def execute(self, args: dict, context: ToolContext) -> ToolResult:
        sql = args.get("sql", "")

        # 验证 SQL 语法
        if not self._is_safe_sql(sql):
            return ToolResult(success=False, error="SQL 包含不安全的操作")

        # 添加 LIMIT 防止大结果集
        if "LIMIT" not in sql.upper():
            sql = f"{sql} LIMIT 1000"

        # 执行...
```

### 5.5 迁移策略：并行运行 + 同时优化

#### 确认的方案
- **迁移方式**：并行运行，新增 `/agent-chat` 端点
- **SQL 质量优化**：同时进行，更换 Embedding 模型

---

## 六、实施计划（最终）

### 阶段 1：基础设施准备

| 任务 | 文件 | 说明 |
|-----|------|------|
| 1.1 创建 vanna_tools.py | `backend/app/services/vanna_tools.py` | 新建，实现 `GenerateSqlTool`、`ExecuteSqlTool` |
| 1.2 创建 vanna_enhancer.py | `backend/app/services/vanna_enhancer.py` | 新建，实现 `VannaContextEnhancer` |
| 1.3 添加依赖 | `backend/requirements.txt` | 添加 `sentence-transformers` |

### 阶段 2：Agent Manager 实现

| 任务 | 文件 | 说明 |
|-----|------|------|
| 2.1 添加 VannaAgentManager | `backend/app/services/vanna_manager.py` | 保留 Legacy 代码，新增 Agent 管理类 |
| 2.2 更新 Embedding 模型 | `backend/app/services/vanna_manager.py` | 使用 `paraphrase-multilingual-MiniLM-L12-v2` |
| 2.3 调整检索参数 | `backend/app/services/vanna_manager.py` | `n_results_sql=15`, `n_results_ddl=10` |

### 阶段 3：API 端点

| 任务 | 文件 | 说明 |
|-----|------|------|
| 3.1 添加 /agent-chat 端点 | `backend/app/api/v1/endpoints/chat.py` | 流式响应，SSE/NDJSON |
| 3.2 添加路由注册 | `backend/app/api/v1/api.py` | 注册新端点 |

### 阶段 4：测试与验证

| 任务 | 文件 | 说明 |
|-----|------|------|
| 4.1 单元测试 | `backend/tests/test_vanna_agent.py` | 新建，测试 Agent 功能 |
| 4.2 集成测试 | `backend/tests/test_agent_chat_api.py` | 新建，测试 API 端点 |

---

## 七、关键代码清单

### 需要新建的文件
1. `backend/app/services/vanna_tools.py` - 自定义 Agent Tools
2. `backend/app/services/vanna_enhancer.py` - LLM Context Enhancer

### 需要修改的文件
1. `backend/app/services/vanna_manager.py` - 添加 VannaAgentManager
2. `backend/app/api/v1/endpoints/chat.py` - 添加 /agent-chat 端点
3. `backend/requirements.txt` - 添加 sentence-transformers

### 保留不变的文件
1. 现有 `/chat` 端点 - 继续使用 Legacy API
2. 现有训练数据逻辑 - 共享给 Agent
