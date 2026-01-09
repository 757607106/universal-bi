# PostgreSQL 元数据与向量存储统一架构优化

## 变更概述

将项目从 MySQL + ChromaDB + PostgreSQL(PGVector) 四数据库架构简化为 PostgreSQL + DuckDB 双数据库架构，实现业务元数据与向量数据的统一存储管理。

### 变更目标

- 使用 PostgreSQL 替代 MySQL 作为主业务数据库，存储所有元数据表
- 启用 PostgreSQL 的 pgvector 扩展替代 ChromaDB，统一向量数据存储
- 保留 DuckDB 用于数据分析场景
- 保留 Redis 用于缓存
- 移除 MySQL 和 ChromaDB 依赖，简化架构

### 影响范围

| 变更类型 | 影响模块 | 变更说明 |
|---------|---------|---------|
| 数据库架构 | 主业务数据库 | MySQL → PostgreSQL |
| 向量存储 | Vanna 训练数据 | ChromaDB → PostgreSQL pgvector |
| 配置管理 | 环境变量与配置类 | 移除 MySQL/ChromaDB 配置项，调整 PostgreSQL 配置 |
| 数据模型 | SQLAlchemy ORM | 验证兼容性，调整数据类型映射 |
| 部署架构 | Docker Compose | 移除 MySQL 服务，调整 PostgreSQL 服务 |
| 数据迁移 | 数据库表结构与数据 | 从 MySQL 迁移至 PostgreSQL |

## 架构对比

### 当前架构（四数据库）

```mermaid
graph TB
    subgraph "当前架构"
        App[Backend Application]
        MySQL[(MySQL<br/>元数据存储)]
        PG[(PostgreSQL<br/>PGVector)]
        Chroma[(ChromaDB<br/>文件存储)]
        Duck[(DuckDB<br/>分析计算)]
        Redis[(Redis<br/>缓存)]
        
        App -->|业务数据| MySQL
        App -->|向量数据<br/>可选| PG
        App -->|向量数据<br/>默认| Chroma
        App -->|分析查询| Duck
        App -->|缓存| Redis
    end
```

### 目标架构（双数据库）

```mermaid
graph TB
    subgraph "目标架构"
        App[Backend Application]
        PG[(PostgreSQL<br/>元数据 + 向量)]
        Duck[(DuckDB<br/>分析计算)]
        Redis[(Redis<br/>缓存)]
        
        App -->|业务数据<br/>向量数据| PG
        App -->|分析查询| Duck
        App -->|缓存| Redis
    end
```

## PostgreSQL 数据库设计

### 数据库命名与结构

| 数据库用途 | 数据库名称 | 说明 |
|-----------|-----------|------|
| 业务元数据 + 向量存储 | `universal_bi` | 统一存储所有业务表和向量数据表 |

### 扩展插件要求

PostgreSQL 数据库需启用以下扩展：

| 扩展名称 | 用途 | 安装命令 |
|---------|------|---------|
| pgvector | 向量相似度搜索 | `CREATE EXTENSION IF NOT EXISTS vector;` |

### 元数据表设计

沿用现有 SQLAlchemy 模型定义，主要包含以下表：

| 表名 | 用途 | 主要字段 |
|------|------|---------|
| users | 用户管理 | id, username, email, hashed_password, company, is_superuser |
| datasources | 数据源连接 | id, name, type, host, port, database_name, owner_id |
| datasets | 数据集定义 | id, name, datasource_id, collection_name, status, duckdb_path, owner_id |
| business_terms | 业务术语 | id, dataset_id, term, definition, owner_id |
| computed_metrics | 计算指标 | id, dataset_id, name, formula, description |
| chat_sessions | 聊天会话 | id, title, dataset_id, owner_id, created_at |
| chat_messages | 会话消息 | id, session_id, question, answer, sql, chart_data, insight |
| dashboards | 仪表盘 | id, name, description, owner_id |
| dashboard_cards | 仪表盘卡片 | id, dashboard_id, title, dataset_id, sql, chart_type |
| dashboard_templates | 仪表盘模板 | id, name, config, is_public |
| training_logs | 训练日志 | id, dataset_id, content, created_at |
| data_tables | 数据表管理 | id, name, owner_id, file_path, row_count |

### 向量数据表结构

由 `pgvector` 和 `langchain-postgres` 库自动创建和管理：

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| langchain_pg_collection | 向量集合管理 | uuid, name, cmetadata |
| langchain_pg_embedding | 向量嵌入存储 | uuid, collection_id, embedding(vector), document, cmetadata |

每个数据集（dataset_id）对应三个向量集合：
- `vec_ds_{dataset_id}_ddl` - 存储 DDL 表结构
- `vec_ds_{dataset_id}_documentation` - 存储业务文档
- `vec_ds_{dataset_id}_sql` - 存储 QA 问答对

## 配置变更方案

### 环境变量调整

#### 移除的配置项

以下环境变量不再使用，需从 `.env` 和 `.env.example` 中移除：

```
# MySQL 配置（完全移除）
MYSQL_ROOT_PASSWORD
MYSQL_DATABASE
MYSQL_PORT

# ChromaDB 配置（完全移除）
CHROMA_PERSIST_DIR
CHROMA_N_RESULTS
```

#### 新增/调整的配置项

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| SQLALCHEMY_DATABASE_URI | PostgreSQL 主数据库连接字符串 | `postgresql://postgres:password@localhost:5432/universal_bi` |
| PG_HOST | PostgreSQL 主机地址 | `localhost` |
| PG_PORT | PostgreSQL 端口 | `5432` |
| PG_DB | PostgreSQL 数据库名 | `universal_bi` |
| PG_USER | PostgreSQL 用户名 | `postgres` |
| PG_PASSWORD | PostgreSQL 密码 | `secure_password` |
| VECTOR_STORE_TYPE | 向量存储类型（固定值） | `pgvector` |
| VECTOR_N_RESULTS | 向量检索返回结果数量 | `10` |

#### 保留的配置项

| 配置项 | 用途 | 说明 |
|--------|------|------|
| REDIS_URL | Redis 缓存连接 | 保持不变 |
| REDIS_CACHE_TTL | 缓存过期时间 | 保持不变 |
| DUCKDB_DATABASE_DIR | DuckDB 存储目录 | 保持不变 |
| DASHSCOPE_API_KEY | 通义千问 API 密钥 | 保持不变 |
| QWEN_MODEL | AI 模型名称 | 保持不变 |

### 配置类重构

`backend/app/core/config.py` 需进行以下调整：

#### 移除的属性

```
VN_PG_HOST, VN_PG_PORT, VN_PG_DB, VN_PG_USER, VN_PG_PASSWORD
VN_PG_CONNECTION_STRING (property)
CHROMA_PERSIST_DIR
CHROMA_N_RESULTS
```

#### 新增/调整的属性

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| PG_HOST | str | "localhost" | PostgreSQL 主机地址 |
| PG_PORT | int | 5432 | PostgreSQL 端口 |
| PG_DB | str | "universal_bi" | PostgreSQL 数据库名 |
| PG_USER | str | "postgres" | PostgreSQL 用户名 |
| PG_PASSWORD | str | "postgres" | PostgreSQL 密码 |
| PG_CONNECTION_STRING | property | - | 动态生成连接字符串 |
| VECTOR_STORE_TYPE | str | "pgvector" | 固定为 pgvector |
| VECTOR_N_RESULTS | int | 10 | 向量检索结果数量 |

#### 配置属性计算方法

| 属性方法 | 返回值示例 | 用途 |
|---------|-----------|------|
| PG_CONNECTION_STRING | `postgresql://postgres:password@localhost:5432/universal_bi` | 提供给 Vanna 和数据库连接 |

## 代码变更方案

### 数据库连接层

#### 主数据库连接（backend/app/db/session.py）

**变更点**：
- 调整默认连接字符串从 MySQL 格式改为 PostgreSQL 格式
- 连接池配置保持不变，兼容 PostgreSQL

**兼容性检查项**：
- SQLAlchemy 引擎创建逻辑适配 PostgreSQL
- 连接池参数（pool_size, max_overflow, pool_recycle）对 PostgreSQL 同样有效
- `pool_pre_ping` 参数保持启用，确保连接健康检查

#### 数据库初始化（backend/init_db.py）

**变更点**：
- 使用 PostgreSQL 驱动（`psycopg2` 或 `asyncpg`）
- 执行 pgvector 扩展初始化：`CREATE EXTENSION IF NOT EXISTS vector;`
- 创建所有元数据表结构

### Vanna 服务层

#### 实例管理器（backend/app/services/vanna/instance_manager.py）

**变更策略**：
- 移除 ChromaDB 相关代码分支（`_get_global_chroma_client`, `_delete_chromadb_collection`）
- 移除 `VECTOR_STORE_TYPE` 条件判断，固定使用 `VannaLegacyPGVector`
- 所有向量操作统一使用 PGVector 后端

**方法变更**：

| 方法名 | 变更类型 | 变更说明 |
|--------|---------|---------|
| `_get_global_chroma_client` | 删除 | 不再需要 ChromaDB 客户端 |
| `get_legacy_vanna` | 简化 | 移除 ChromaDB 分支，仅保留 PGVector 逻辑 |
| `get_agent` | 调整 | 将 `ChromaAgentMemory` 替换为 `PGVectorAgentMemory`（如果使用 Agent 模式） |
| `delete_collection` | 简化 | 移除 ChromaDB 分支，仅保留 `_delete_pgvector_collection` |
| `_delete_chromadb_collection` | 删除 | 不再需要 |

#### Vanna 基础类（backend/app/services/vanna/base.py）

**变更策略**：
- 移除 `VannaLegacy` 类（基于 ChromaDB）
- 保留并优化 `VannaLegacyPGVector` 类
- 确保所有向量操作使用统一的 PostgreSQL 连接

**类变更**：

| 类名 | 变更类型 | 说明 |
|------|---------|------|
| `VannaLegacy` | 删除 | 移除 ChromaDB 实现 |
| `VannaLegacyPGVector` | 保留并重命名 | 建议重命名为 `VannaLegacy`，简化命名 |

#### 训练数据服务（backend/app/services/vanna/training_data_service.py）

**变更策略**：
- 移除 ChromaDB 后端支持逻辑
- 简化 `get_training_data` 方法，移除 `vector_store_type` 判断
- 所有训练数据操作直接调用 PGVector 相关方法

**方法变更**：

| 方法名 | 变更说明 |
|--------|---------|
| `get_training_data` | 移除 ChromaDB 分支，固定使用 PGVector 查询逻辑 |
| `delete_training_data` | 移除 ChromaDB 分支，固定使用 PGVector 删除逻辑 |

### 数据模型层

#### SQLAlchemy 模型（backend/app/models/metadata.py）

**兼容性检查**：

| 数据类型 | MySQL 类型 | PostgreSQL 类型 | 兼容性 | 备注 |
|---------|-----------|---------------|-------|------|
| String | VARCHAR | VARCHAR | ✅ 兼容 | 长度限制保持一致 |
| Integer | INT | INTEGER | ✅ 兼容 | 自增主键自动映射 |
| Text | TEXT | TEXT | ✅ 兼容 | 大文本字段 |
| JSON | JSON | JSONB | ⚠️ 需验证 | PostgreSQL 推荐使用 JSONB |
| DateTime | DATETIME | TIMESTAMP | ✅ 兼容 | 时区处理需统一 |
| Boolean | TINYINT(1) | BOOLEAN | ✅ 兼容 | SQLAlchemy 自动处理 |

**需调整的字段**：

| 模型 | 字段 | 调整方案 |
|------|------|---------|
| 所有模型 | JSON 类型字段 | 建议显式使用 `JSONB` 类型以提升性能 |
| 所有模型 | DateTime 字段 | 统一使用 UTC 时区，避免时区歧义 |

### 数据迁移脚本

#### 迁移脚本目录（backend/migrations/）

**变更策略**：
- 将现有 MySQL 初始化脚本（`000_init_schema.sql` ~ `20260109_add_session_and_template.sql`）改写为 PostgreSQL 兼容语法
- 新增 pgvector 扩展初始化脚本

**语法差异处理**：

| 语法特性 | MySQL | PostgreSQL | 处理方案 |
|---------|-------|-----------|---------|
| 自增主键 | AUTO_INCREMENT | SERIAL / GENERATED ALWAYS AS IDENTITY | 使用 SERIAL |
| 引擎声明 | ENGINE=InnoDB | - | 移除 ENGINE 子句 |
| 字符集声明 | CHARSET=utf8mb4 | - | 移除 CHARSET 子句，PostgreSQL 默认 UTF-8 |
| 反引号标识符 | \`table_name\` | "table_name" | 统一使用双引号或移除 |
| TINYINT | TINYINT(1) | SMALLINT 或 BOOLEAN | 布尔类型用 BOOLEAN，小整数用 SMALLINT |
| 时间戳默认值 | DEFAULT CURRENT_TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 兼容，保持不变 |

#### 迁移脚本执行器（backend/run_migration.py）

**变更点**：
- 适配 PostgreSQL 驱动（`psycopg2`）
- 调整连接字符串解析逻辑
- 保留事务控制和错误处理机制

**移除的脚本**：
- `backend/run_mysql_migration.py` - 专用于 MySQL 的迁移脚本可删除

### 部署相关

#### Docker Compose 配置（docker-compose.yml）

**服务变更**：

| 操作 | 服务名 | 变更说明 |
|------|--------|---------|
| 删除 | mysql | 移除整个 MySQL 服务定义 |
| 调整 | postgres | 调整数据库名称为 `universal_bi`，启用 pgvector 扩展 |
| 调整 | backend | 更新环境变量，移除 MySQL 相关配置 |
| 保留 | redis | 保持不变 |

**卷（Volumes）变更**：

| 操作 | 卷名 | 说明 |
|------|------|------|
| 删除 | mysql_data | 移除 MySQL 数据卷 |
| 删除 | chroma_data | 移除 ChromaDB 数据卷 |
| 保留 | postgres_data | PostgreSQL 数据持久化 |
| 保留 | redis_data | Redis 数据持久化 |

**后端服务环境变量**：

移除：
```
SQLALCHEMY_DATABASE_URI=mysql+pymysql://...
```

新增：
```
SQLALCHEMY_DATABASE_URI=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
PG_HOST=postgres
PG_PORT=5432
PG_DB=${POSTGRES_DB:-universal_bi}
PG_USER=postgres
PG_PASSWORD=${POSTGRES_PASSWORD}
VECTOR_STORE_TYPE=pgvector
```

移除：
```
VN_PG_HOST, VN_PG_PORT, VN_PG_DB, VN_PG_USER, VN_PG_PASSWORD
```

#### PostgreSQL 服务配置

**新增初始化脚本卷映射**：

将 PostgreSQL 初始化脚本目录映射到容器：
```
volumes:
  - postgres_data:/var/lib/postgresql/data
  - ./backend/migrations:/docker-entrypoint-initdb.d
```

**扩展初始化**：

在 `backend/migrations/000_init_extension.sql`（新建）中添加：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Dockerfile 调整

**后端 Dockerfile（Dockerfile.backend）**：

移除 ChromaDB 相关依赖（如已在 requirements.txt 中）：
- chromadb

确保包含 PostgreSQL 驱动：
- psycopg2-binary 或 asyncpg
- langchain-postgres
- langchain-huggingface（用于向量嵌入）

### 测试与验证

#### 单元测试调整

**测试文件变更范围**：

| 测试文件 | 变更类型 | 说明 |
|---------|---------|------|
| test_vanna_integration.py | 调整 | 移除 ChromaDB 相关测试，验证 PGVector 集成 |
| test_training_api.py | 调整 | 确保训练数据存储至 PostgreSQL |
| test_comprehensive_chat.py | 调整 | 验证向量检索从 PostgreSQL 读取 |

**测试数据库配置**：
- 使用 PostgreSQL 测试数据库（如 `universal_bi_test`）
- 测试前确保 pgvector 扩展已安装

#### 集成测试清单

| 测试场景 | 验证点 | 预期结果 |
|---------|--------|---------|
| 数据库连接 | 主数据库连接成功 | 成功创建 SessionLocal |
| 表结构创建 | 所有元数据表创建 | 无 SQL 语法错误 |
| pgvector 扩展 | vector 扩展可用 | `SELECT * FROM pg_extension WHERE extname='vector'` 返回结果 |
| 训练数据存储 | DDL/Documentation/SQL 存储 | 数据写入 langchain_pg_embedding 表 |
| 向量检索 | 相似度搜索 | 返回相关训练数据 |
| 数据集删除 | 清理向量集合 | langchain_pg_collection 中对应记录删除 |
| DuckDB 分析 | 多表分析功能 | 保持现有功能正常 |

## 数据迁移策略

### 迁移准备

#### 数据备份

| 备份对象 | 备份方式 | 存储位置 |
|---------|---------|---------|
| MySQL 数据库 | `mysqldump` 导出 SQL | `./backup/mysql_dump.sql` |
| ChromaDB 数据 | 复制持久化目录 | `./backup/chroma_db/` |

#### 环境准备

| 准备项 | 检查命令 | 要求 |
|--------|---------|------|
| PostgreSQL 版本 | `psql --version` | >= 12 |
| pgvector 扩展 | `SELECT * FROM pg_available_extensions WHERE name='vector'` | 已安装 |
| Python 依赖 | `pip list \| grep -E "psycopg2\|langchain-postgres"` | 已安装 |

### 迁移步骤

#### 第一阶段：数据库结构迁移

1. 执行 PostgreSQL 初始化脚本，创建所有业务表
2. 验证表结构完整性（表数量、字段定义、索引、外键）
3. 执行 pgvector 扩展初始化

#### 第二阶段：业务数据迁移

**方式一：逻辑迁移（推荐小规模数据）**

使用 ETL 脚本逐表迁移数据：
- 从 MySQL 读取数据
- 转换数据类型（JSON → JSONB）
- 写入 PostgreSQL

**方式二：物理迁移（推荐大规模数据）**

使用专业迁移工具：
- pgloader（自动转换 MySQL 到 PostgreSQL）
- AWS DMS（如在云环境）

**迁移顺序（按依赖关系）**：

1. users
2. datasources
3. datasets
4. datasources 的外键关联表
5. datasets 的外键关联表（business_terms, training_logs, chat_sessions, computed_metrics）
6. chat_messages
7. dashboards
8. dashboard_cards, dashboard_templates
9. data_tables

#### 第三阶段：向量数据迁移

**策略选择**：

| 方案 | 适用场景 | 迁移方式 |
|------|---------|---------|
| 重新训练 | 训练数据量较小 | 删除旧数据，重新调用训练接口 |
| 数据转换 | 需保留训练历史 | 从 ChromaDB 导出向量，转换格式后导入 PGVector |

**推荐方案**：重新训练

理由：
- ChromaDB 与 PGVector 的嵌入格式不完全兼容
- 重新训练可使用统一的嵌入模型
- 训练过程可验证新系统稳定性

**重新训练流程**：

1. 获取所有数据集列表（`SELECT id FROM datasets`）
2. 对每个数据集，调用训练接口重新训练 DDL、业务术语、QA 对
3. 验证训练数据已写入 `langchain_pg_embedding` 表

#### 第四阶段：验证与切换

**验证清单**：

| 验证项 | 验证方式 | 通过标准 |
|--------|---------|---------|
| 数据完整性 | 对比表行数 | MySQL 与 PostgreSQL 行数一致 |
| 数据准确性 | 抽样对比关键字段 | 数据内容一致 |
| 向量检索 | 执行测试查询 | 返回相关结果 |
| 业务功能 | 执行端到端测试 | 所有功能正常 |

**切换步骤**：

1. 停止应用服务
2. 更新 `.env` 配置文件
3. 重启应用服务
4. 执行冒烟测试
5. 监控日志，确认无异常

### 回滚预案

**触发条件**：
- 迁移后出现严重数据错误
- 业务功能严重异常
- 性能严重下降

**回滚步骤**：

1. 停止应用服务
2. 恢复原 `.env` 配置（指向 MySQL）
3. 恢复 MySQL 数据库（如有数据变更）
4. 恢复 ChromaDB 数据（从备份目录）
5. 重启应用服务

**回滚时间窗口**：

保留 MySQL 和 ChromaDB 数据 30 天，确保可安全回滚。

## 性能优化建议

### PostgreSQL 配置优化

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| shared_buffers | 25% 可用内存 | 提升缓存命中率 |
| effective_cache_size | 50% 可用内存 | 查询计划优化 |
| work_mem | 16MB ~ 64MB | 排序和哈希操作 |
| maintenance_work_mem | 256MB ~ 1GB | 索引创建和维护 |
| max_connections | 100 ~ 200 | 根据并发量调整 |

### 向量检索优化

| 优化策略 | 实施方式 | 预期效果 |
|---------|---------|---------|
| 索引优化 | 为 embedding 列创建 HNSW 或 IVFFlat 索引 | 加速相似度搜索 |
| 分区策略 | 按 collection_id 分区 | 减少扫描范围 |
| 缓存预热 | 应用启动时加载热点向量 | 减少首次查询延迟 |

### 查询性能监控

| 监控指标 | 查询方式 | 阈值 |
|---------|---------|------|
| 慢查询 | pg_stat_statements | > 1s |
| 连接池使用率 | pg_stat_activity | > 80% |
| 缓存命中率 | pg_statio_user_tables | < 90% |

## 兼容性与风险评估

### 技术兼容性

| 组件 | 兼容性 | 风险级别 | 说明 |
|------|--------|---------|------|
| SQLAlchemy ORM | ✅ 高 | 低 | PostgreSQL 为官方支持数据库 |
| FastAPI | ✅ 高 | 低 | 与数据库类型无关 |
| Vanna AI | ✅ 高 | 低 | 已支持 PGVector 后端 |
| DuckDB | ✅ 高 | 低 | 独立运行，不受影响 |
| Redis | ✅ 高 | 低 | 独立运行，不受影响 |

### 功能影响评估

| 功能模块 | 影响程度 | 风险 | 缓解措施 |
|---------|---------|------|---------|
| 用户认证 | 无影响 | 低 | 数据完整迁移即可 |
| 数据源管理 | 无影响 | 低 | 数据完整迁移即可 |
| 数据集训练 | 中等影响 | 中 | 需重新训练向量数据 |
| 自然语言查询 | 中等影响 | 中 | 验证向量检索准确性 |
| 仪表盘功能 | 无影响 | 低 | 数据完整迁移即可 |
| 多表分析 | 无影响 | 低 | DuckDB 独立运行 |

### 已知风险与应对

| 风险项 | 风险等级 | 应对策略 |
|--------|---------|---------|
| 数据迁移失败 | 高 | 充分测试，准备回滚方案 |
| 向量检索性能下降 | 中 | 建立向量索引，优化配置 |
| SQL 语法不兼容 | 中 | 迁移前充分验证，必要时调整代码 |
| 时区处理差异 | 低 | 统一使用 UTC，显式处理时区转换 |
| JSON 字段性能 | 低 | 使用 JSONB，建立 GIN 索引 |

## 依赖项调整

### Python 依赖变更

#### requirements.txt 变更

**移除的依赖**：
```
chromadb
pymysql
```

**新增的依赖**：
```
psycopg2-binary==2.9.9
langchain-postgres==0.0.6
langchain-huggingface==0.0.1
```

**保留的依赖**：
```
sqlalchemy
vanna
redis
duckdb
fastapi
```

### 系统依赖

| 依赖项 | 用途 | 安装方式 |
|--------|------|---------|
| PostgreSQL 客户端库 | Python 驱动依赖 | 系统包管理器安装 libpq-dev |
| pgvector 扩展 | PostgreSQL 插件 | 通过 PostgreSQL 扩展管理器或编译安装 |

## 文档与培训

### 需要更新的文档

| 文档名称 | 更新内容 | 优先级 |
|---------|---------|--------|
| README.md | 架构图，技术栈说明 | 高 |
| INSTALLATION_GUIDE.md | 移除 MySQL 安装步骤，新增 pgvector 安装 | 高 |
| .env.example | 配置项示例更新 | 高 |
| docker-compose.yml 注释 | 服务说明更新 | 中 |
| docs/backend/*.md | 向量数据库配置相关文档 | 中 |
| API 文档 | 训练数据接口说明（如有影响） | 低 |

### 开发者指南更新

#### 本地开发环境搭建

**PostgreSQL 安装与配置**：
- macOS: `brew install postgresql@15`
- Ubuntu: `apt install postgresql-15 postgresql-contrib-15`
- Windows: 下载官方安装包

**pgvector 扩展安装**：
- macOS: `brew install pgvector`
- Ubuntu: `apt install postgresql-15-pgvector`
- Windows: 参考官方编译指南

#### 数据初始化流程

1. 创建数据库：`createdb universal_bi`
2. 启用扩展：`psql universal_bi -c "CREATE EXTENSION vector;"`
3. 执行迁移脚本：`python backend/run_migration.py`
4. 初始化管理员：`python backend/set_superuser.py`

## 实施时间表

| 阶段 | 任务 | 预计工期 | 依赖 |
|------|------|---------|------|
| 准备阶段 | 环境搭建、依赖安装、备份数据 | 1 天 | - |
| 开发阶段 | 代码调整、配置修改、迁移脚本编写 | 3 天 | 准备阶段 |
| 测试阶段 | 单元测试、集成测试、性能测试 | 2 天 | 开发阶段 |
| 迁移阶段 | 数据迁移、向量重训练、验证 | 2 天 | 测试阶段 |
| 部署阶段 | 更新文档、发布版本、监控 | 1 天 | 迁移阶段 |

总计：9 个工作日

## 验收标准

### 功能验收

| 验收项 | 验收标准 | 验证方式 |
|--------|---------|---------|
| 用户登录 | 正常登录，Token 生成正确 | 手动测试 + 自动化测试 |
| 数据源连接 | 创建、编辑、删除数据源 | 功能测试 |
| 数据集训练 | 训练成功，进度正常，日志完整 | 功能测试 |
| 自然语言查询 | 返回正确 SQL，结果准确 | 功能测试 + 准确率统计 |
| 向量检索 | 相似度搜索返回相关结果 | 单元测试 + 集成测试 |
| 仪表盘展示 | 图表正常渲染，数据更新 | 功能测试 |
| 多表分析 | DuckDB 分析功能正常 | 功能测试 |

### 性能验收

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 数据库连接建立时间 | < 200ms | 性能测试工具 |
| 向量检索响应时间 | < 500ms（10 个结果） | 性能测试工具 |
| 自然语言查询总耗时 | < 5s（包含 LLM 调用） | 端到端测试 |
| 并发用户支持 | 100 并发无异常 | 压力测试 |

### 数据验收

| 验收项 | 验收标准 | 验证方式 |
|--------|---------|---------|
| 数据完整性 | 所有表行数与 MySQL 一致 | SQL 对比查询 |
| 数据准确性 | 关键字段抽样对比 100% 一致 | 数据校验脚本 |
| 向量数据可用性 | 每个数据集的三个向量集合均存在 | SQL 查询 langchain_pg_collection |
| 外键约束 | 所有外键约束生效 | SQL 查询约束信息 |

## 附录

### PostgreSQL 与 MySQL 语法差异速查表

| 特性 | MySQL | PostgreSQL | 备注 |
|------|-------|-----------|------|
| 字符串连接 | CONCAT() | \|\| 或 CONCAT() | 两者都支持 CONCAT() |
| 限制结果数 | LIMIT n | LIMIT n | 兼容 |
| 偏移结果 | LIMIT n OFFSET m | OFFSET m LIMIT n | 顺序可互换 |
| 日期格式化 | DATE_FORMAT() | TO_CHAR() | 函数名不同 |
| 当前时间 | NOW() | NOW() 或 CURRENT_TIMESTAMP | 兼容 |
| 自增主键 | AUTO_INCREMENT | SERIAL 或 IDENTITY | 语法不同 |
| 布尔类型 | TINYINT(1) | BOOLEAN | 类型不同 |
| JSON 字段 | JSON | JSON 或 JSONB | PostgreSQL 推荐 JSONB |
| 全文搜索 | FULLTEXT INDEX | tsvector + GIN INDEX | 机制不同 |

### 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| pgvector 扩展创建失败 | 扩展未安装 | 安装 postgresql-15-pgvector 包 |
| 向量检索结果为空 | 训练数据未写入 | 检查 langchain_pg_embedding 表，重新训练 |
| 连接池耗尽 | max_connections 设置过低 | 调整 PostgreSQL 配置或优化连接池参数 |
| JSON 字段查询慢 | 未建立索引 | 为 JSONB 字段创建 GIN 索引 |
| 时区显示不一致 | 时区处理差异 | 统一使用 UTC，显式转换时区 |

### 参考资源

| 资源类型 | 名称 | 链接 |
|---------|------|------|
| 官方文档 | PostgreSQL 官方文档 | https://www.postgresql.org/docs/ |
| 扩展文档 | pgvector GitHub | https://github.com/pgvector/pgvector |
| 库文档 | langchain-postgres | https://python.langchain.com/docs/integrations/vectorstores/pgvector |
| 迁移工具 | pgloader | https://github.com/dimitri/pgloader |
| SQLAlchemy | PostgreSQL 方言 | https://docs.sqlalchemy.org/en/20/dialects/postgresql.html |
