# 技术栈详细说明书

## 1. 前端架构
- **核心框架**: Vue 3.4+ (Composition API)
- **构建工具**: Vite 5+
- **语言**: TypeScript 5.x
- **UI 组件库**: Element Plus (针对中后台场景优化)
- **CSS 框架**: Tailwind CSS 3.x (原子化 CSS)
- **图表库**: Apache ECharts 5.x
- **状态管理**: Pinia
- **路由**: Vue Router 4.x
- **HTTP 客户端**: Axios (封装拦截器处理 JWT)

## 2. 后端架构
- **Web 框架**: FastAPI
- **语言**: Python 3.10+
- **数据库交互**:
  - **SQLAlchemy (Async)**: 用于操作系统自身的元数据表。
  - **SQLAlchemy Core (Reflection)**: 用于反射读取用户连接的外部数据库。
- **AI 引擎**:
  - **Vanna**: Text-to-SQL 框架 (工厂模式，支持多租户)。
  - **LLM**: 通义千问 (Qwen-Turbo/Max) via DashScope API。
  - **Vector DB**: PostgreSQL + pgvector。
- **任务队列/缓存**: Redis (用于缓存 SQL 查询结果)。

## 3. 基础设施
- **容器化**: Docker & Docker Compose
- **数据库**: PostgreSQL 16 (官方镜像 + pgvector 插件)