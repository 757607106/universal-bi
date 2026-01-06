# Universal BI 项目完整结构文档

> 最后更新：2026-01-06  
> 本文档详细描述了 Universal BI 项目的完整目录结构、各模块职责及关键技术实现。

## 📁 根目录结构

```text
universal-bi/
├── .cursor/                # Cursor AI 配置
│   └── rules/
│       └── bi.mdc          # 项目规则文档
├── .git/                   # Git 版本控制
├── .gitignore              # Git 忽略文件配置
├── README.md               # 项目说明文档
├── requirements.txt        # Python 依赖列表
├── backend/                # 后端项目（FastAPI + Vanna AI）
├── frontend/               # 前端项目（Vue 3 + TypeScript）
└── docs/                   # 项目文档
    ├── 1_prd.md            # 产品需求文档
    ├── 2_tech_stack.md     # 技术选型文档
    └── 3_project_structure.md  # 本文档
```

---

## 🔧 后端项目结构 (`backend/`)

### 完整目录树

```text
backend/
├── app/                           # 主应用目录
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── api/                       # API 路由层
│   │   ├── __init__.py
│   │   └── v1/                    # API v1 版本
│   │       ├── __init__.py
│   │       └── endpoints/         # API 端点
│   │           ├── __init__.py
│   │           ├── chat.py        # Chat BI 对话接口
│   │           ├── dashboard.py   # 仪表盘 CRUD 接口
│   │           ├── dataset.py     # Dataset 管理接口
│   │           └── datasource.py  # 数据源管理接口
│   ├── core/                      # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py              # 系统配置（模型、API Key 等）
│   │   └── security.py            # 安全功能（密码加密）
│   ├── db/                        # 数据库配置
│   │   ├── __init__.py
│   │   └── session.py             # SQLAlchemy Session 管理
│   ├── models/                    # ORM 数据模型
│   │   ├── __init__.py
│   │   ├── base.py                # Base 模型类
│   │   └── metadata.py            # 元数据模型
│   │       ├── DataSource         # 数据源模型
│   │       ├── Dataset            # 数据集模型
│   │       ├── DatasetTable       # 数据集-表关联
│   │       ├── Dashboard          # 仪表盘模型
│   │       └── DashboardCard      # 仪表盘卡片模型
│   ├── schemas/                   # Pydantic Schema (API 输入输出)
│   │   ├── __init__.py
│   │   ├── chat.py                # Chat 请求/响应 Schema
│   │   ├── dashboard.py           # Dashboard Schema
│   │   ├── dataset.py             # Dataset Schema
│   │   └── datasource.py          # DataSource Schema
│   └── services/                  # 业务逻辑服务层
│       ├── __init__.py
│       ├── db_inspector.py        # 数据库连接与元数据检查
│       └── vanna_manager.py       # Vanna AI SQL 生成核心服务
│           ├── VannaLegacy        # Legacy API 封装类
│           ├── VannaManager       # Vanna 管理器
│           └── generate_result()  # SQL 生成与执行主函数
├── scripts/                       # 工具脚本
│   ├── generate_fake_data.py      # 生成测试数据脚本
│   └── train_qa_fix.py            # QA 训练脚本（修正表名幻觉）
├── tests/                         # 测试文件
│   └── test_training_flow.py      # 训练流程测试
└── [调试脚本]                      # 开发调试用脚本
    ├── check_async.py
    ├── check_async_llm.py
    ├── check_inheritance.py
    ├── inspect_dataset_tables.py
    ├── inspect_models.py
    ├── inspect_more.py
    ├── inspect_openai.py
    ├── inspect_signatures.py
    ├── inspect_vanna.py
    └── verify_chat_fix.py
```

### 🔑 核心模块说明

#### 1. API 层 (`api/v1/endpoints/`)

| 文件 | 职责 | 主要端点 |
|------|------|----------|
| `chat.py` | Chat BI 对话功能 | `POST /chat/` - 自然语言查询 |
| `dashboard.py` | 仪表盘管理 | CRUD 操作 + 卡片管理 |
| `dataset.py` | 数据集管理 | 创建、训练、查询 Dataset |
| `datasource.py` | 数据源管理 | 连接测试、CRUD 操作 |

#### 2. 服务层 (`services/`)

**`vanna_manager.py` - Vanna AI 核心服务**
- **VannaLegacy 类**：封装 Vanna Legacy API，支持 DashScope 自定义端点
- **VannaManager 类**：
  - `get_agent()` - 获取 Vanna 2.0 Agent（用于训练）
  - `get_legacy_vanna()` - 获取 Legacy Vanna 实例（用于 SQL 生成）
  - `train_dataset()` - 训练数据集（提取 DDL）
  - `generate_result()` - 生成 SQL 并执行查询

**`db_inspector.py` - 数据库检查服务**
- 支持 MySQL、PostgreSQL
- 测试连接、获取表列表、提取 DDL

#### 3. 数据模型 (`models/metadata.py`)

```python
DataSource         # 数据源（存储连接信息，密码加密）
  ├── id, name, db_type, host, port, database
  └── username, password_encrypted

Dataset            # 数据集（AI 的知识边界）
  ├── id, name, datasource_id
  └── tables: List[DatasetTable]

DatasetTable       # 数据集包含的表
  ├── id, dataset_id, table_name
  └── ddl

Dashboard          # 仪表盘
  ├── id, name, description
  └── cards: List[DashboardCard]

DashboardCard      # 仪表盘卡片
  ├── id, dashboard_id, dataset_id
  ├── title, sql, chart_type
  └── layout (JSON)
```

#### 4. 配置文件 (`core/config.py`)

```python
class Settings:
    DASHSCOPE_API_KEY: str       # 通义千问 API Key
    QWEN_MODEL: str = "qwen-max" # 使用的模型
    SQLALCHEMY_DATABASE_URI: str # 元数据库连接
```

---

## 🎨 前端项目结构 (`frontend/`)

### 完整目录树

```text
frontend/
├── index.html                    # HTML 入口
├── package.json                  # NPM 依赖配置
├── package-lock.json             # 依赖锁定文件
├── vite.config.ts                # Vite 构建配置
├── tsconfig.json                 # TypeScript 配置
├── tailwind.config.js            # Tailwind CSS 配置
├── postcss.config.js             # PostCSS 配置
└── src/                          # 源代码目录
    ├── main.ts                   # Vue 应用入口
    ├── App.vue                   # 根组件（路由容器）
    ├── style.css                 # 全局样式（Tailwind）
    ├── vite-env.d.ts             # Vite 类型声明
    ├── api/                      # API 调用封装
    │   ├── chat.ts               # Chat API
    │   ├── dashboard.ts          # Dashboard API
    │   ├── dataset.ts            # Dataset API
    │   └── datasource.ts         # DataSource API
    ├── router/                   # Vue Router 配置
    │   └── index.ts              # 路由定义
    ├── composables/              # Vue 组合式函数
    │   └── useTheme.ts           # 主题切换逻辑
    ├── components/               # 可复用组件
    │   ├── Charts/
    │   │   └── DynamicChart.vue  # 动态图表组件（ECharts）
    │   ├── AddConnectionDialog.vue      # 添加数据源弹窗
    │   ├── ChatBI.vue                   # Chat BI 主组件
    │   ├── ConnectionCard.vue           # 数据源卡片
    │   ├── Dashboard.vue                # 仪表盘组件（已弃用，迁移到 views）
    │   ├── DataConnectionHub.vue        # 数据源管理主页
    │   ├── DataPreviewDrawer.vue        # 数据预览抽屉
    │   ├── DatasetBuilder.vue           # Dataset 构建器
    │   ├── DeleteConfirmDialog.vue      # 删除确认弹窗
    │   ├── SQLViewDialog.vue            # SQL 查看弹窗
    │   ├── ThemeToggle.vue              # 主题切换按钮
    │   └── TrainingProgressDialog.vue   # 训练进度弹窗
    └── views/                    # 页面视图（路由页面）
        ├── Chat/
        │   └── index.vue         # Chat BI 页面
        ├── Dashboard/
        │   ├── index.vue         # 仪表盘列表页
        │   └── Detail.vue        # 仪表盘详情页
        └── Dataset/
            ├── index.vue         # Dataset 管理页
            └── components/
                └── DatasetWizard.vue  # Dataset 创建向导
```

### 🔑 核心模块说明

#### 1. 路由配置 (`router/index.ts`)

```typescript
Routes:
  / (root)          → Chat BI 页面
  /dataset          → Dataset 管理页
  /dashboard        → 仪表盘列表页
  /dashboard/:id    → 仪表盘详情页
```

#### 2. API 封装 (`api/`)

每个 API 文件封装对应模块的 HTTP 请求：
- 统一使用 Axios
- 定义 TypeScript 接口
- 基础 URL: `http://localhost:8000/api/v1`

#### 3. 核心组件说明

| 组件 | 职责 | 位置 |
|------|------|------|
| `ChatBI.vue` | Chat BI 对话界面 | `components/` |
| `DatasetBuilder.vue` | Dataset 表选择与训练 | `components/` |
| `DynamicChart.vue` | 动态图表渲染（支持柱状图、折线图、饼图、表格）| `components/Charts/` |
| `DataConnectionHub.vue` | 数据源管理页面 | `components/` |
| `Dashboard/Detail.vue` | 仪表盘详情（驾驶舱）| `views/Dashboard/` |

#### 4. 技术栈

- **框架**：Vue 3 (Composition API) + TypeScript
- **构建工具**：Vite
- **UI 组件**：Element Plus
- **CSS**：Tailwind CSS
- **图表**：ECharts + vue-echarts
- **路由**：Vue Router
- **HTTP 客户端**：Axios

---

## 📦 依赖管理

### 后端依赖 (`requirements.txt`)

```text
fastapi
uvicorn
sqlalchemy
pydantic
pydantic-settings
pymysql
psycopg2-binary
pandas
cryptography
vanna
openai
chromadb
```

### 前端依赖 (主要)

```json
{
  "vue": "^3.4.0",
  "vue-router": "^4.0.0",
  "element-plus": "^2.5.0",
  "echarts": "^5.5.0",
  "vue-echarts": "^7.0.0",
  "axios": "^1.6.0",
  "tailwindcss": "^3.4.0",
  "vite": "^5.0.0"
}
```

---

## 🗄️ 数据流架构

### Chat BI 查询流程

```mermaid
用户输入问题
  ↓
Chat/index.vue (前端)
  ↓ HTTP POST /api/v1/chat/
chat.py (API 端点)
  ↓
vanna_manager.py (服务层)
  ├─ 1. 获取 Dataset 和 DataSource
  ├─ 2. 初始化 VannaLegacy (Legacy API)
  ├─ 3. 调用 generate_sql() - RAG 检索 + LLM 生成
  ├─ 4. 执行 SQL (pandas.read_sql)
  ├─ 5. 推断图表类型
  └─ 6. 返回结果
  ↓
DynamicChart.vue 渲染图表
```

### Dataset 训练流程

```mermaid
用户选择表 → 点击训练
  ↓
DatasetBuilder.vue
  ↓ POST /api/v1/datasets/{id}/train
dataset.py
  ↓
vanna_manager.py::train_dataset()
  ├─ 1. 获取 Dataset 和 DataSource
  ├─ 2. 连接目标数据库
  ├─ 3. 提取所选表的 DDL
  ├─ 4. 保存 DDL 到 dataset_tables
  ├─ 5. 调用 Vanna Agent.train_ddl()
  └─ 6. 存储到 ChromaDB (collection: vec_ds_{id})
```

---

## 🔧 关键技术实现

### 1. Vanna AI 集成

**问题背景**：Vanna 2.0 Agent Memory 和 Legacy API 检索机制不兼容

**解决方案**：
- **训练阶段**：使用 Vanna 2.0 Agent (支持 DDL 训练)
- **生成阶段**：使用 Vanna Legacy API (支持 QA 对检索)
- 共享 ChromaDB collection 存储

```python
# 训练 - 使用 Vanna 2.0 Agent
agent = VannaManager.get_agent(dataset_id)
await agent.train_ddl(ddl_text)

# 生成 - 使用 Legacy API
vn = VannaManager.get_legacy_vanna(dataset_id)
sql = vn.generate_sql(question)  # 自动 RAG + LLM
```

### 2. 模型选择

- **qwen-turbo**：速度快，但不严格遵守 prompt（会返回引导性回答）
- **qwen-max**：✅ 推荐，严格遵守 prompt，稳定返回 SQL

### 3. 密码加密

使用 `cryptography.fernet` 加密数据源密码：

```python
from cryptography.fernet import Fernet

cipher = Fernet(settings.SECRET_KEY)
encrypted = cipher.encrypt(password.encode()).decode()
```

### 4. SQLAlchemy Eager Loading

防止 N+1 查询和 lazy loading 问题：

```python
from sqlalchemy.orm import selectinload

stmt = select(Dataset).options(selectinload(Dataset.datasource))
```

---

## 📝 开发规范

### 代码组织原则

1. **后端分层**：API → Services → Models → DB
2. **前端分层**：Views → Components → API → Utils
3. **命名规范**：
   - Python: snake_case
   - TypeScript: camelCase
   - Vue 组件: PascalCase

### Git 提交规范

```text
feat: 新功能
fix: 修复 Bug
refactor: 重构
docs: 文档更新
style: 代码格式
test: 测试相关
chore: 构建/工具配置
```

---

## 🚀 启动指南

### 后端启动

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev  # 默认 http://localhost:3000
```

---

## 📚 相关文档

- [1_prd.md](./1_prd.md) - 产品需求文档
- [2_tech_stack.md](./2_tech_stack.md) - 技术选型文档
- [README.md](../README.md) - 项目使用说明

---

> **维护说明**：本文档需要随项目结构变化及时更新。
