# Universal BI 项目完整结构文档

> **文档版本**: v1.2  
> **最后更新**: 2026-01-08  
> 本文档详细描述了 Universal BI 项目的完整目录结构、各模块职责及关键技术实现。

## 📁 根目录结构

```text
universal-bi/
├── .env.example            # 环境变量模板文件
├── setup.sh                # Linux/macOS 一键部署脚本
├── setup.bat               # Windows 一键部署脚本
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile.backend      # 后端 Docker 镜像配置
├── Dockerfile.frontend     # 前端 Docker 镜像配置
├── README.md               # 项目说明文档
├── QUICKSTART.md           # 快速开始指南
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
│   │   ├── deps.py                # 全局依赖 (Auth, DB)
│   │   └── v1/endpoints/          # API 端点
│   │       ├── admin.py           # 管理员接口 (用户管理)
│   │       ├── auth.py            # 认证接口 (登录/注册)
│   │       ├── chat.py            # Chat BI 对话接口
│   │       ├── dashboard.py       # 仪表盘 CRUD 接口
│   │       ├── dataset.py         # Dataset 管理接口
│   │       └── datasource.py      # 数据源管理接口
│   ├── core/                      # 核心配置
│   │   ├── config.py              # 系统配置（模型、API Key 等）
│   │   ├── logger.py              # 结构化日志配置
│   │   ├── redis.py               # Redis 连接配置
│   │   └── security.py            # 安全功能（密码加密、JWT）
│   ├── db/                        # 数据库配置
│   │   └── session.py             # SQLAlchemy Session 管理
│   ├── models/                    # ORM 数据模型
│   │   ├── base.py                # Base 模型类
│   │   └── metadata.py            # 元数据模型 (DataSource, Dataset, User 等)
│   ├── schemas/                   # Pydantic Schema (API 输入输出)
│   │   ├── chat.py                # Chat 请求/响应 Schema
│   │   ├── dashboard.py           # Dashboard Schema
│   │   ├── dataset.py             # Dataset Schema
│   │   ├── datasource.py          # DataSource Schema
│   │   ├── token.py               # Token Schema
│   │   └── user.py                # User Schema
│   └── services/                  # 业务逻辑服务层
│       ├── db_inspector.py        # 数据库连接与元数据检查
│       ├── vanna/                 # Vanna AI 模块化服务
│       │   ├── __init__.py        # 公共接口导出
│       │   ├── base.py            # VannaLegacy 基础类
│       │   ├── instance_manager.py# 实例生命周期管理
│       │   ├── training_service.py# 训练服务
│       │   ├── sql_generator.py   # SQL 生成与执行
│       │   ├── cache_service.py   # Redis 缓存服务
│       │   ├── analyst_service.py # 业务分析服务
│       │   ├── training_data_service.py # 训练数据 CRUD
│       │   ├── agent_manager.py   # Vanna 2.0 Agent API
│       │   ├── facade.py          # VannaManager 外观类
│       │   └── utils.py           # 工具方法
│       ├── vanna_tools.py         # Agent 工具定义
│       ├── vanna_enhancer.py      # LLM 上下文增强器
│       └── vanna_manager.py       # 向后兼容入口
├── migrations/                    # 数据库迁移脚本
│   ├── 000_init_schema.sql        # 数据库初始化 SQL
│   ├── 001_add_saas_features.sql
│   ├── 002_add_user_admin_fields.sql
│   ├── 003_add_training_status_fields.sql
│   └── 004_add_user_company.sql
├── scripts/                       # 工具脚本
│   ├── generate_fake_data.py      # 生成测试数据脚本
│   └── train_qa_fix.py            # QA 训练脚本
├── tests/                         # 测试文件
│   ├── manual_scripts/            # 手动测试脚本
│   └── test_*.py                  # 自动化测试
├── clear_cache.py                 # Redis 缓存清理工具
├── init_db.py                     # 数据库初始化脚本
├── monitor_redis.py               # Redis 监控脚本
├── run_migration.py               # 迁移运行入口
├── set_superuser.py               # 设置超级管理员脚本
└── requirements.txt               # 后端依赖
```

### 🔑 核心模块说明

#### 1. API 层 (`api/v1/endpoints/`)

| 文件 | 职责 | 主要端点 |
|------|------|----------|
| `auth.py` | 用户认证 | `POST /login`, `POST /register`, `POST /logout` |
| `admin.py` | 系统管理 | `GET /users`, `PATCH /users/{id}/status` |
| `chat.py` | Chat BI 对话功能 | `POST /chat/` - 自然语言查询 |
| `dashboard.py` | 仪表盘管理 | CRUD 操作 + 卡片管理 |
| `dataset.py` | 数据集管理 + 可视化建模 | 创建、训练、查询 Dataset；AI 分析关联；创建视图 |
| `datasource.py` | 数据源管理 | 连接测试、CRUD 操作 |

#### 2. 服务层 (`services/vanna/`)

**模块化 Vanna AI 服务架构：**

| 模块 | 职责 |
|------|------|
| `base.py` | VannaLegacy 基础类定义 |
| `instance_manager.py` | Vanna 实例生命周期管理（单例、缓存） |
| `training_service.py` | DDL/文档/QA 训练功能 |
| `sql_generator.py` | SQL 生成、执行、多轮推理 |
| `cache_service.py` | Redis 缓存读写 |
| `analyst_service.py` | 业务分析、数据洞察 |
| `training_data_service.py` | 训练数据 CRUD 操作 |
| `agent_manager.py` | Vanna 2.0 Agent API 支持 |
| `facade.py` | VannaManager 外观类（统一入口） |

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
  ├── status, process_rate  # 训练状态
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
├── nginx.conf                    # Nginx 配置（Docker 生产环境）
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
│   │   ├── Charts/DynamicChart.vue
│   │   ├── AddConnectionDialog.vue
│   │   ├── ConnectionCard.vue
│   │   ├── DataConnectionHub.vue
│   │   ├── DataPreviewDrawer.vue
│   │   ├── DeleteConfirmDialog.vue
│   │   ├── SQLViewDialog.vue
│   │   ├── Sidebar.vue
│   │   ├── ThemeToggle.vue
│   │   └── TrainingProgressDialog.vue
│   ├── layout/                   # 布局组件
│   │   └── MainLayout.vue        # 主布局 (Sidebar + Header)
│   ├── router/                   # 路由配置
│   │   └── index.ts
│   ├── store/modules/            # Pinia 状态管理
│   │   └── user.ts               # 用户状态 (Token, UserInfo)
│   ├── utils/                    # 工具函数
│   │   ├── http/index.ts         # Axios 封装
│   │   └── auth.ts               # Token 管理
│   └── views/                    # 页面视图
│       ├── Chat/index.vue        # Chat BI 页面
│       ├── Dashboard/            # 仪表盘相关页面
│       │   ├── index.vue
│       │   └── Detail.vue
│       ├── Dataset/              # Dataset 管理页面
│       │   ├── index.vue         # 数据集列表
│       │   └── modeling/         # 可视化建模模块
│       │       ├── index.vue     # 建模主页面 (VueFlow 画布)
│       │       └── components/
│       │           └── TableNode.vue
│       ├── Login/                # 登录/注册页面
│       └── System/User/          # 系统管理页面
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

#### 2. 可视化建模模块 (`views/Dataset/modeling/`)

- **三栏布局**：表选择器(20%) + VueFlow画布(60%) + 属性面板(20%)
- **手动连线**：VueFlow `connect-on-click` 模式
- **连线编辑**：右侧面板字段选择器
- **SQL生成**：自动去重列名并添加别名

---

## 📚 文档索引

### 通用文档 (`docs/general/`)

| 文件 | 说明 |
|------|------|
| `1_prd.md` | 产品需求文档 |
| `2_tech_stack.md` | 技术栈说明 |
| `3_project_structure.md` | 项目结构（本文档） |
| `4_feature_status.md` | 功能完成状态 |

### 后端文档 (`docs/backend/`)

| 文件 | 说明 |
|------|------|
| `IMPLEMENTATION_SUMMARY.md` | 实现总结 |
| `REDIS_CACHE.md` | Redis 缓存指南 |
| `SAAS_UPGRADE_GUIDE.md` | SaaS 升级指南 |
| `FEEDBACK_RLHF.md` | 反馈闭环机制 |
| `MULTI_ROUND_REASONING.md` | 多轮推理机制 |
| `ANALYST_AGENT.md` | 分析师 Agent |
| `SCHEMA_INJECTION.md` | Schema 注入 |
| `CACHE_CONTROL_TESTING.md` | 缓存控制测试 |
| `TRAINING_CONTROL_GUIDE.md` | 训练控制指南 |

### 前端文档 (`docs/frontend/`)

| 文件 | 说明 |
|------|------|
| `FEEDBACK_USER_GUIDE.md` | 反馈功能用户指南 |
| `TEST_CLARIFICATION.md` | 测试说明 |

---

> **维护说明**：本文档需要随项目结构变化及时更新。
