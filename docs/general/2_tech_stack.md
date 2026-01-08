# 技术栈详细说明书

> **文档版本**: v1.2  
> **最后更新**: 2026-01-08

## 1. 前端架构

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **核心框架** | Vue 3 | 3.4+ | Composition API |
| **构建工具** | Vite | 5+ | 快速开发构建 |
| **语言** | TypeScript | 5.x | 类型安全 |
| **UI 组件库** | Element Plus | - | 中后台 UI 组件 |
| **CSS 框架** | Tailwind CSS | 3.x | 原子化 CSS |
| **图表库** | Apache ECharts | 5.x | 数据可视化 |
| **状态管理** | Pinia | - | 响应式状态管理 |
| **路由** | Vue Router | 4.x | SPA 路由管理 |
| **HTTP 客户端** | Axios | - | 封装拦截器处理 JWT |
| **可视化建模** | VueFlow | - | 拖拽式画布、节点连线 |

## 2. 后端架构

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | FastAPI | - | 高性能异步 API |
| **语言** | Python | 3.10+ | 主要开发语言 |
| **ORM** | SQLAlchemy | Async | 数据库交互、ORM 映射 |
| **数据验证** | Pydantic | v2 | 请求/响应 Schema |
| **认证** | JWT | - | OAuth2 + Bearer Token |
| **日志** | structlog | - | 结构化日志 |

### 2.1 AI 引擎

| 组件 | 技术 | 说明 |
|------|------|------|
| **Text-to-SQL** | Vanna 2.0 | 工厂模式，支持多租户 |
| **LLM** | 通义千问 (Qwen) | DashScope API (qwen-max/qwen-turbo) |
| **向量数据库** | ChromaDB | 本地持久化，Collection 隔离 |
| **上下文增强** | 自定义 Enhancer | 多语言支持、Schema 注入 |

### 2.2 服务模块化架构

```
backend/app/services/
├── vanna/                      # Vanna AI 模块化服务
│   ├── base.py                 # VannaLegacy 基础类
│   ├── instance_manager.py     # 实例生命周期管理
│   ├── training_service.py     # 训练服务
│   ├── sql_generator.py        # SQL 生成与执行
│   ├── cache_service.py        # Redis 缓存服务
│   ├── analyst_service.py      # 业务分析服务
│   ├── training_data_service.py# 训练数据 CRUD
│   ├── agent_manager.py        # Vanna 2.0 Agent API
│   └── facade.py               # VannaManager 外观类
├── vanna_tools.py              # Agent 工具定义
├── vanna_enhancer.py           # LLM 上下文增强器
├── vanna_manager.py            # 向后兼容入口
└── db_inspector.py             # 数据库元数据检查
```

## 3. 基础设施

| 组件 | 技术 | 用途 |
|------|------|------|
| **容器化** | Docker & Docker Compose | 一键部署 |
| **元数据库** | PostgreSQL 16 / MySQL 8 | 系统元数据存储 |
| **缓存** | Redis | SQL 查询缓存、Token 黑名单 |
| **向量存储** | ChromaDB | 训练数据向量化存储 |
| **反向代理** | Nginx | 前端静态资源、API 代理 |

## 4. 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────┬─────────────┬─────────────┬───────────────┤
│   Frontend  │   Backend   │    MySQL    │     Redis     │
│   (Nginx)   │  (FastAPI)  │  (Primary)  │    (Cache)    │
│   :80       │   :8000     │   :3306     │    :6379      │
└─────────────┴─────────────┴─────────────┴───────────────┘
         │              │
         │              └── ChromaDB (本地持久化)
         │
         └── 静态资源 + API 反向代理
```

## 5. 核心依赖 (后端)

```
fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
redis>=5.0.0
vanna>=2.0.0
dashscope>=1.14.0
chromadb>=0.4.0
pandas>=2.0.0
pymysql>=1.1.0
psycopg2-binary>=2.9.9
structlog>=24.1.0
cryptography>=42.0.0
```

## 6. 核心依赖 (前端)

```json
{
  "vue": "^3.4.0",
  "vue-router": "^4.2.0",
  "pinia": "^2.1.0",
  "element-plus": "^2.5.0",
  "axios": "^1.6.0",
  "echarts": "^5.4.0",
  "vue-echarts": "^6.6.0",
  "@vue-flow/core": "^1.26.0",
  "@vue-flow/background": "^1.2.0",
  "@vue-flow/controls": "^1.0.0",
  "tailwindcss": "^3.4.0",
  "typescript": "^5.3.0"
}
```
