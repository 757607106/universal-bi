# Universal BI 项目完整结构文档

> 最后更新：2026-01-07 (v1.1)  
> 本文档详细描述了 Universal BI 项目的完整目录结构、各模块职责及关键技术实现。

## 📁 根目录结构

```text
universal-bi/
├── .cursor/                # Cursor AI 配置
│   └── rules/
│       └── bi.mdc          # 项目规则文档
├── .git/                   # Git 版本控制
├── .gitignore              # Git 忽略文件配置
├── .env.example            # 环境变量模板文件 ✨
├── setup.sh                # Linux/macOS 一键部署脚本 ✨
├── setup.bat               # Windows 一键部署脚本 ✨
├── docker-compose.yml      # Docker Compose 配置 ✨
├── Dockerfile.backend      # 后端 Docker 镜像配置 ✨
├── Dockerfile.frontend     # 前端 Docker 镜像配置 ✨
├── README.md               # 项目说明文档
├── QUICKSTART.md           # 快速开始指南 ✨
├── requirements.txt        # Python 依赖列表
├── backend/                # 后端项目（FastAPI + Vanna AI）
├── frontend/               # 前端项目（Vue 3 + TypeScript）
└── docs/                   # 项目文档中心
    ├── backend/            # 后端相关文档
    ├── frontend/           # 前端相关文档
    └── general/            # 通用/全局文档 (PRD, 架构, 状态)
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
│   │   ├── deps.py                # 全局依赖 (Auth, DB)
│   │   └── v1/                    # API v1 版本
│   │       ├── __init__.py
│   │       └── endpoints/         # API 端点
│   │           ├── admin.py       # 管理员接口 (用户管理)
│   │           ├── auth.py        # 认证接口 (登录/注册)
│   │           ├── chat.py        # Chat BI 对话接口
│   │           ├── dashboard.py   # 仪表盘 CRUD 接口
│   │           ├── dataset.py     # Dataset 管理接口
│   │           └── datasource.py  # 数据源管理接口
│   ├── core/                      # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py              # 系统配置（模型、API Key 等）
│   │   └── security.py            # 安全功能（密码加密、JWT）
│   ├── db/                        # 数据库配置
│   │   ├── __init__.py
│   │   └── session.py             # SQLAlchemy Session 管理
│   ├── models/                    # ORM 数据模型
│   │   ├── __init__.py
│   │   ├── base.py                # Base 模型类
│   │   └── metadata.py            # 元数据模型 (DataSource, Dataset, User 等)
│   ├── schemas/                   # Pydantic Schema (API 输入输出)
│   │   ├── __init__.py
│   │   ├── chat.py                # Chat 请求/响应 Schema
│   │   ├── dashboard.py           # Dashboard Schema
│   │   ├── dataset.py             # Dataset Schema
│   │   ├── datasource.py          # DataSource Schema
│   │   ├── token.py               # Token Schema
│   │   └── user.py                # User Schema
│   └── services/                  # 业务逻辑服务层
│       ├── __init__.py
│       ├── db_inspector.py        # 数据库连接与元数据检查
│       └── vanna_manager.py       # Vanna AI SQL 生成核心服务
├── migrations/                    # 数据库迁移脚本
│   ├── 000_init_schema.sql        # 数据库初始化 SQL ✨
│   ├── 001_add_saas_features.sql
│   └── 002_add_user_admin_fields.sql
├── scripts/                       # 工具脚本
│   ├── generate_fake_data.py      # 生成测试数据脚本
│   └── train_qa_fix.py            # QA 训练脚本
├── tests/                         # 测试文件
│   ├── manual_scripts/            # 手动测试脚本 (原根目录 test_*.py)
│   └── test_training_flow.py      # 训练流程测试
├── init_db.py                     # 数据库初始化脚本 ✨
├── monitor_redis.py               # Redis 监控脚本
├── requirements.txt               # 后端依赖
└── run_migration.py               # 迁移运行入口
```

### 🔑 核心模块说明

#### 1. API 层 (`api/v1/endpoints/`)

| 文件 | 职责 | 主要端点 |
|------|------|----------|
| `auth.py` | 用户认证 | `POST /login`, `POST /register` |
| `admin.py` | 系统管理 | `GET /users`, `PATCH /users/{id}/status` |
| `chat.py` | Chat BI 对话功能 | `POST /chat/` - 自然语言查询 |
| `dashboard.py` | 仪表盘管理 | CRUD 操作 + 卡片管理 |
| `dataset.py` | 数据集管理 + 可视化建模 | 创建、训练、查询 Dataset；AI 分析关联；创建视图 |
| `datasource.py` | 数据源管理 | 连接测试、CRUD 操作 |

#### 2. 服务层 (`services/`)

**`vanna_manager.py` - Vanna AI 核心服务**
- **VannaLegacy 类**：封装 Vanna Legacy API，支持 DashScope 自定义端点
  - **关键修复 (2026-01-07)**：修复自定义 `chroma_client` 初始化时缺失父类属性导致的 AttributeError
  - 正确初始化 `VannaBase` 属性：`config`, `dialect`, `language`, `max_tokens`, `run_sql_is_set`, `static_documentation`
  - 正确初始化 `ChromaDB_VectorStore` 属性：`n_results_sql`, `n_results_documentation`, `n_results_ddl`
- **VannaManager 类**：
  - `get_agent()` - 获取 Vanna 2.0 Agent（用于训练）
  - `get_legacy_vanna()` - 获取 Legacy Vanna 实例（用于 SQL 生成）
  - `train_dataset()` - 训练数据集（提取 DDL）
  - `generate_result()` - 生成 SQL 并执行查询

**`db_inspector.py` - 数据库检查服务**
- 支持 MySQL、PostgreSQL
- 测试连接、获取表列表、提取 DDL

#### 4. 可视化建模核心函数 (`endpoints/dataset.py`) ✨

**`_deduplicate_sql_columns()` - SQL 重复列名去重**
- 解析 SELECT 子句，检测重复列名
- 为重复列自动添加表别名前缀（如 `u.user_id AS u_user_id`）
- 解决 MySQL/PostgreSQL 创建视图时重复列名报错问题

**相关 API 端点**：
- `POST /datasets/analyze` - AI 分析表关联关系
- `POST /datasets/create_view` - 创建数据库视图（宽表）

#### 3. 数据模型 (`models/metadata.py`)

```python
User                 # 用户模型 (SaaS 核心)
  ├── id, email, hashed_password
  ├── is_active, is_superuser, role
  └── owner_id (多租户隔离)

DataSource           # 数据源
  ├── id, name, db_type, host, ...
  ├── owner_id       # 数据隔离
  └── password_encrypted

Dataset              # 数据集
  ├── id, name, datasource_id
  ├── owner_id       # 数据隔离
  └── tables: List[DatasetTable]

Dashboard            # 仪表盘
  ├── id, name, description
  ├── owner_id       # 数据隔离
  └── cards: List[DashboardCard]
```

---

## 🎨 前端项目结构 (`frontend/`)

### 完整目录树

```text
frontend/
├── index.html                    # HTML 入口
├── package.json                  # NPM 依赖配置
├── vite.config.ts                # Vite 构建配置
├── nginx.conf                    # Nginx 配置（Docker 生产环境） ✨
├── src/                          # 源代码目录
│   ├── main.ts                   # Vue 应用入口
│   ├── App.vue                   # 根组件
│   ├── api/                      # API 调用封装
│   │   ├── chat.ts               # Chat API
│   │   ├── dashboard.ts          # Dashboard API
│   │   ├── dataset.ts            # Dataset API (含建模接口)
│   │   ├── datasource.ts         # DataSource API
│   │   ├── user.ts               # 用户 Auth API
│   │   └── system.ts             # 系统管理 API
│   ├── components/               # 可复用组件
│   │   ├── Charts/               # 图表组件
│   │   │   └── DynamicChart.vue
│   │   ├── ReIcon/               # 图标组件
│   │   ├── AddConnectionDialog.vue
│   │   ├── ConnectionCard.vue
│   │   ├── DataConnectionHub.vue # 数据源管理组件
│   │   ├── DataPreviewDrawer.vue
│   │   ├── DeleteConfirmDialog.vue
│   │   ├── Sidebar.vue           # 侧边栏
│   │   ├── ThemeToggle.vue
│   │   └── ...
│   ├── layout/                   # 布局组件
│   │   └── MainLayout.vue        # 主布局 (Sidebar + Header)
│   ├── router/                   # 路由配置
│   │   └── index.ts
│   ├── store/                    # Pinia 状态管理
│   │   └── modules/
│   │       └── user.ts           # 用户状态 (Token, UserInfo)
│   ├── utils/                    # 工具函数
│   │   ├── http/                 # Axios 封装
│   │   └── auth.ts               # Token 管理
│   └── views/                    # 页面视图
│       ├── Chat/                 # Chat BI 页面
│       ├── Dashboard/            # 仪表盘相关页面
│       ├── Dataset/              # Dataset 管理页面
│       │   ├── index.vue         # 数据集列表
│       │   └── modeling/         # 可视化建模模块 ✨
│       │       ├── index.vue     # 建模主页面 (VueFlow 画布)
│       │       └── components/
│       │           └── TableNode.vue  # 表节点组件
│       ├── Login/                # 登录/注册页面
│       └── System/               # 系统管理页面
```

### 🔑 核心模块说明

#### 1. 路由配置 (`router/index.ts`)

```typescript
Routes:
  /login            → 登录页
  / (MainLayout)    → 需要 Auth 守卫
    ├── /connections  → 数据源管理
    ├── /datasets     → 数据集管理
    ├── /chat         → Chat BI
    ├── /dashboard    → 仪表盘列表
    └── /system/user  → 用户管理 (Require Superuser)
```

#### 2. 技术栈

- **框架**：Vue 3 (Composition API) + TypeScript
- **状态管理**：Pinia
- **UI 组件**：Element Plus
- **CSS**：Tailwind CSS
- **图表**：ECharts + vue-echarts
- **可视化建模**：@vue-flow/core + @vue-flow/background + @vue-flow/controls ✨
- **HTTP**：Axios (拦截器处理 Token 和 401)

#### 3. 可视化建模模块 (`views/Dataset/modeling/`) ✨

**`index.vue` - 建模主页面**
- 三栏布局：表选择器(20%) + VueFlow画布(60%) + 属性面板(20%)
- 支持拖拽/双击添加表到画布
- **手动连线**：VueFlow `connect-on-click` 模式
- **连线编辑**：右侧面板字段选择器 + `handleUpdateEdge()`
- **连线删除**：`removeEdges()` API
- **SQL生成**：`generateSQL()` 自动去重列名并添加别名

**`components/TableNode.vue` - 表节点组件**
- 显示表名、字段列表(前5个)、字段类型图标
- 左侧绿色 Handle (target) + 右侧蓝色 Handle (source)

---

## 🚀 部署相关配置

### 环境配置文件

**`.env.example` - 环境变量模板**
- 包含所有必要的配置项说明
- 支持多种数据库（MySQL/PostgreSQL/SQLite）
- AI 模型配置（DASHSCOPE_API_KEY、QWEN_MODEL）
- Redis 缓存配置
- 向量数据库配置（ChromaDB、PGVector）

### 一键部署脚本

**`setup.sh` (Linux/macOS)**
- 自动检测操作系统和依赖环境
- 支持开发模式部署（本地安装依赖）
- 支持 Docker 模式部署（容器化）
- 自动创建 .env 配置文件
- 生成开发环境启动脚本

**`setup.bat` (Windows)**
- Windows 完整支持
- 功能与 setup.sh 一致
- 彩色命令行输出

### Docker 配置

**`docker-compose.yml`**
- 一键启动所有服务：MySQL、PostgreSQL、Redis、后端、前端
- 包含健康检查和自动重启
- 数据持久化配置
- 服务依赖管理

**`Dockerfile.backend`**
- Python 3.10 基础镜像
- 自动安装系统依赖（MySQL、PostgreSQL 客户端）
- 使用阿里云镜像加速

**`Dockerfile.frontend`**
- 多阶段构建（Node.js builder + Nginx）
- 生产优化配置
- 自动构建和部署

**`frontend/nginx.conf`**
- SPA 路由支持
- API 反向代理
- Gzip 压缩
- 静态资源缓存

### 数据库初始化

**`backend/init_db.py`**
- 自动创建数据库表结构
- 插入默认管理员账户
- 支持幂等执行

**`backend/migrations/000_init_schema.sql`**
- MySQL/PostgreSQL 初始化脚本
- Docker Compose 自动执行
- 包含索引和约束

---

## 📚 文档索引

所有文档均已归档至 `docs/` 目录：

- **通用文档** (`docs/general/`)
  - [1_prd.md](./1_prd.md) - 产品需求
  - [2_tech_stack.md](./2_tech_stack.md) - 技术栈
  - [3_project_structure.md](./3_project_structure.md) - 项目结构（本文档）
  - [4_feature_status.md](./4_feature_status.md) - 功能状态

- **后端文档** (`docs/backend/`)
  - [IMPLEMENTATION_SUMMARY.md](../backend/IMPLEMENTATION_SUMMARY.md) - 实现总结
  - [REDIS_CACHE.md](../backend/REDIS_CACHE.md) - Redis 缓存指南
  - [SAAS_UPGRADE_GUIDE.md](../backend/SAAS_UPGRADE_GUIDE.md) - SaaS 升级指南

- **前端文档** (`docs/frontend/`)
  - [TEST_CLARIFICATION.md](../frontend/TEST_CLARIFICATION.md) - 测试说明

- **快速开始**
  - [QUICKSTART.md](../../QUICKSTART.md) - 5 分钟快速部署指南 ✨
  - [README.md](../../README.md) - 项目主文档

---

> **维护说明**：本文档需要随项目结构变化及时更新。  
> **最后更新**: 2026-01-07 (v1.1) - 添加可视化建模模块、连线功能、SQL去重相关内容；记录 VannaLegacy 初始化 bug 修复
