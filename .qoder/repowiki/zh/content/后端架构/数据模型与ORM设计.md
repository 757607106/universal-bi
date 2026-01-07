# 数据模型与ORM设计

<cite>
**本文档引用的文件**
- [metadata.py](file://backend/app/models/metadata.py)
- [base.py](file://backend/app/models/base.py)
- [session.py](file://backend/app/db/session.py)
- [config.py](file://backend/app/core/config.py)
- [deps.py](file://backend/app/api/deps.py)
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py)
- [user.py](file://backend/app/schemas/user.py)
- [dataset.py](file://backend/app/schemas/dataset.py)
- [dashboard.py](file://backend/app/schemas/dashboard.py)
- [datasource.py](file://backend/app/schemas/datasource.py)
- [chat.py](file://backend/app/schemas/chat.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介

本项目采用SQLAlchemy作为ORM框架，构建了一个完整的数据分析平台。本文档深入分析了基于SQLAlchemy的ORM设计，重点解析了metadata.py中的模型定义、base.py中的通用字段抽象、以及schemas目录下的Pydantic模型与数据库模型之间的映射关系。

该系统实现了完整的数据所有权控制机制，支持公共资源和私有资源的混合管理模式，通过owner_id外键关联实现细粒度的数据访问控制。

## 项目结构

项目采用分层架构设计，主要分为以下几个层次：

```mermaid
graph TB
subgraph "表现层"
API[API端点]
Frontend[前端界面]
end
subgraph "业务逻辑层"
Services[业务服务]
Handlers[处理器]
end
subgraph "数据访问层"
Models[ORM模型]
Schemas[Pydantic模型]
Session[数据库会话]
end
subgraph "基础设施"
Config[配置管理]
Security[安全认证]
end
API --> Handlers
Handlers --> Services
Services --> Models
Models --> Session
Session --> Config
API --> Schemas
Handlers --> Schemas
```

**图表来源**
- [metadata.py](file://backend/app/models/metadata.py#L1-L129)
- [base.py](file://backend/app/models/base.py#L1-L4)
- [session.py](file://backend/app/db/session.py#L1-L34)

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L1-L129)
- [base.py](file://backend/app/models/base.py#L1-L4)
- [session.py](file://backend/app/db/session.py#L1-L34)

## 核心组件

### 基础模型架构

项目的核心是基于SQLAlchemy的DeclarativeBase基类，通过统一的Base类实现所有模型的继承。这种设计提供了以下优势：

- **统一的模型基类**：所有模型共享相同的生命周期管理和元数据
- **一致的字段定义**：通过抽象通用字段减少重复代码
- **标准化的关系映射**：确保模型间关系的一致性和可维护性

### 时间戳管理机制

系统实现了自动化的created_at和updated_at时间戳管理：

```mermaid
sequenceDiagram
participant Client as 客户端
participant Model as 数据模型
participant DB as 数据库
Client->>Model : 创建新记录
Model->>Model : 设置created_at默认值
Model->>DB : 插入记录
DB-->>Model : 返回记录ID
Model-->>Client : 返回完整记录
Client->>Model : 更新记录
Model->>Model : 更新updated_at字段
Model->>DB : 更新记录
DB-->>Model : 确认更新
Model-->>Client : 返回更新后的记录
```

**图表来源**
- [metadata.py](file://backend/app/models/metadata.py#L63-L64)
- [metadata.py](file://backend/app/models/metadata.py#L77-L77)

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L6-L16)
- [metadata.py](file://backend/app/models/metadata.py#L63-L64)
- [metadata.py](file://backend/app/models/metadata.py#L77-L77)

## 架构概览

系统采用MVC架构模式，结合FastAPI的依赖注入机制：

```mermaid
graph TB
subgraph "API层"
Endpoints[端点处理程序]
Dependencies[依赖注入]
end
subgraph "业务层"
BusinessLogic[业务逻辑]
OwnershipFilter[数据所有权过滤]
end
subgraph "数据层"
ORMModels[ORM模型]
PydanticSchemas[Pydantic模型]
Database[数据库]
end
Endpoints --> BusinessLogic
Dependencies --> BusinessLogic
BusinessLogic --> ORMModels
ORMModels --> Database
Endpoints --> PydanticSchemas
BusinessLogic --> PydanticSchemas
```

**图表来源**
- [deps.py](file://backend/app/api/deps.py#L97-L124)
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L64-L78)

## 详细组件分析

### 用户模型 (User)

用户模型是系统的基础实体，定义了用户的基本属性和权限控制：

```mermaid
classDiagram
class User {
+Integer id
+String email
+String hashed_password
+String full_name
+Boolean is_active
+Boolean is_superuser
+Boolean is_deleted
+String role
}
class DataSource {
+Integer id
+String name
+String type
+String host
+Integer port
+String username
+String password_encrypted
+String database_name
+Integer owner_id
}
class Dataset {
+Integer id
+String name
+Integer datasource_id
+String collection_name
+JSON schema_config
+String status
+JSON modeling_config
+Integer process_rate
+Text error_msg
+DateTime last_train_at
+Integer owner_id
}
User "1" --> "many" DataSource : "拥有"
User "1" --> "many" Dataset : "拥有"
```

**图表来源**
- [metadata.py](file://backend/app/models/metadata.py#L6-L16)
- [metadata.py](file://backend/app/models/metadata.py#L18-L32)
- [metadata.py](file://backend/app/models/metadata.py#L35-L53)

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L6-L16)
- [metadata.py](file://backend/app/models/metadata.py#L18-L32)

### 数据源模型 (DataSource)

数据源模型负责管理外部数据库连接信息：

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | 主键 | 数据源唯一标识符 |
| name | String(255) | 唯一、索引 | 数据源名称 |
| type | String(50) |  | 数据库类型（postgresql/mysql） |
| host | String(255) |  | 数据库主机地址 |
| port | Integer |  | 数据库端口号 |
| username | String(255) |  | 用户名 |
| password_encrypted | String(500) |  | 加密后的密码 |
| database_name | String(255) |  | 数据库名称 |
| owner_id | Integer | 外键(users.id) | 所有者ID，为空表示公共资源 |

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L18-L32)

### 数据集模型 (Dataset)

数据集模型是核心业务实体，负责管理数据集的训练状态和配置：

```mermaid
flowchart TD
Start([创建数据集]) --> ValidateDataSource["验证数据源所有权"]
ValidateDataSource --> DataSourceValid{"数据源有效?"}
DataSourceValid --> |否| Error["抛出HTTP异常"]
DataSourceValid --> |是| CreateDataset["创建数据集记录"]
CreateDataset --> SetDefaults["设置默认值<br/>status='pending'<br/>owner_id=当前用户"]
SetDefaults --> GenerateCollectionName["生成集合名称<br/>vec_ds_{id}"]
GenerateCollectionName --> Commit["提交事务"]
Commit --> Success["返回数据集"]
Error --> End([结束])
Success --> End
```

**图表来源**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L29-L62)

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L35-L53)
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L29-L62)

### 仪表板模型 (Dashboard)

仪表板模型支持动态可视化卡片管理：

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | 主键 | 仪表板唯一标识符 |
| name | String(255) | 索引 | 仪表板名称 |
| description | String(500) | 可空 | 描述信息 |
| owner_id | Integer | 外键(users.id) | 所有者ID |
| created_at | DateTime | 默认值 | 创建时间 |
| updated_at | DateTime | 默认值+更新触发器 | 更新时间 |

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L56-L67)

### 业务术语模型 (BusinessTerm)

业务术语模型用于定义数据集中的业务概念：

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | 主键 | 术语唯一标识符 |
| dataset_id | Integer | 外键(datasets.id) | 关联的数据集 |
| term | String(255) | 索引 | 术语名称 |
| definition | Text |  | 术语定义 |
| owner_id | Integer | 外键(users.id) | 所有者ID |
| created_at | DateTime | 默认值 | 创建时间 |

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L98-L109)

### 聊天消息模型 (ChatMessage)

聊天消息模型支持AI对话历史记录：

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | 主键 | 消息唯一标识符 |
| dataset_id | Integer | 外键(datasets.id) | 关联的数据集 |
| user_id | Integer | 外键(users.id) | 发送用户 |
| owner_id | Integer | 外键(users.id) | 所有者ID |
| question | Text |  | 用户问题 |
| answer | Text | 可空 | AI回答 |
| sql | Text | 可空 | 生成的SQL |
| chart_type | String(50) | 可空 | 图表类型 |
| created_at | DateTime | 默认值 | 创建时间 |

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L112-L128)

## 依赖关系分析

### 数据模型依赖图

```mermaid
graph TB
subgraph "核心模型"
User[User]
BaseModel[BaseModel]
end
subgraph "业务模型"
DataSource[DataSource]
Dataset[Dataset]
Dashboard[Dashboard]
BusinessTerm[BusinessTerm]
ChatMessage[ChatMessage]
TrainingLog[TrainingLog]
DashboardCard[DashboardCard]
end
subgraph "关系映射"
User --> DataSource
User --> Dataset
User --> Dashboard
User --> BusinessTerm
User --> ChatMessage
DataSource --> Dataset
Dataset --> BusinessTerm
Dataset --> TrainingLog
Dataset --> DashboardCard
Dashboard --> DashboardCard
end
```

**图表来源**
- [metadata.py](file://backend/app/models/metadata.py#L1-L129)

### 数据所有权过滤机制

系统实现了统一的数据所有权控制机制：

```mermaid
flowchart TD
Request[API请求] --> CheckSuperuser{"是否超级管理员?"}
CheckSuperuser --> |是| AllowAll[允许访问所有数据]
CheckSuperuser --> |否| CheckOwnership["检查数据所有权"]
CheckOwnership --> CheckPublic{"owner_id是否为空?"}
CheckPublic --> |是| AllowPublic[允许访问公共资源]
CheckPublic --> |否| CheckUser{"owner_id是否等于当前用户?"}
CheckUser --> |是| AllowPrivate[允许访问私有数据]
CheckUser --> |否| DenyAccess[拒绝访问]
AllowAll --> Response[返回数据]
AllowPublic --> Response
AllowPrivate --> Response
DenyAccess --> Error[返回403错误]
```

**图表来源**
- [deps.py](file://backend/app/api/deps.py#L97-L124)

**章节来源**
- [deps.py](file://backend/app/api/deps.py#L97-L124)

## 性能考虑

### 数据库连接池配置

系统采用连接池优化数据库连接性能：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| pool_size | 10 | 连接池大小 |
| max_overflow | 20 | 最大溢出连接数 |
| pool_timeout | 30秒 | 获取连接超时时间 |
| pool_recycle | 3600秒 | 连接回收时间 |
| pool_pre_ping | True | 连接前检查可用性 |

### 索引策略

系统针对高频查询字段建立了适当的索引：

- **唯一索引**：email（用户）、collection_name（数据集）
- **普通索引**：name（多表）、owner_id（所有权过滤）
- **组合索引**：根据查询模式优化

## 故障排除指南

### 常见问题及解决方案

1. **数据所有权访问错误**
   - 症状：403 Forbidden错误
   - 原因：普通用户尝试访问非自己拥有的数据
   - 解决：确认用户权限或联系超级管理员

2. **数据库连接超时**
   - 症状：数据库操作超时
   - 原因：连接池配置不当
   - 解决：调整pool_size和pool_timeout参数

3. **时间戳字段异常**
   - 症状：created_at或updated_at字段值异常
   - 原因：时区设置问题
   - 解决：统一使用UTC时间

**章节来源**
- [session.py](file://backend/app/db/session.py#L14-L24)

## 结论

本项目展示了基于SQLAlchemy的ORM设计最佳实践，通过统一的模型基类、清晰的实体关系映射、完善的权限控制机制，构建了一个功能完整、可扩展的数据分析平台。

关键设计亮点包括：
- **模块化设计**：通过Base类实现代码复用
- **权限控制**：基于owner_id的细粒度访问控制
- **自动化管理**：时间戳字段的自动管理机制
- **类型安全**：结合Pydantic模型实现数据验证

## 附录

### 实体关系图（ERD）

```mermaid
erDiagram
USERS {
integer id PK
string email UK
string hashed_password
string full_name
boolean is_active
boolean is_superuser
boolean is_deleted
string role
}
DATASOURCES {
integer id PK
string name
string type
string host
integer port
string username
string password_encrypted
string database_name
integer owner_id FK
}
DATASETS {
integer id PK
string name
integer datasource_id FK
string collection_name UK
json schema_config
string status
json modeling_config
integer process_rate
text error_msg
datetime last_train_at
integer owner_id FK
}
BUSINESS_TERMS {
integer id PK
integer dataset_id FK
string term
text definition
integer owner_id FK
datetime created_at
}
TRAINING_LOGS {
integer id PK
integer dataset_id FK
text content
datetime created_at
}
DASHBOARDS {
integer id PK
string name
string description
integer owner_id FK
datetime created_at
datetime updated_at
}
DASHBOARD_CARDS {
integer id PK
integer dashboard_id FK
string title
integer dataset_id FK
text sql
string chart_type
json layout
datetime created_at
}
CHAT_MESSAGES {
integer id PK
integer dataset_id FK
integer user_id FK
integer owner_id FK
text question
text answer
text sql
string chart_type
datetime created_at
}
USERS ||--o{ DATASOURCES : "拥有"
USERS ||--o{ DATASETS : "拥有"
USERS ||--o{ BUSINESS_TERMS : "拥有"
USERS ||--o{ DASHBOARDS : "拥有"
USERS ||--o{ CHAT_MESSAGES : "拥有"
DATASOURCES ||--o{ DATASETS : "包含"
DATASETS ||--o{ BUSINESS_TERMS : "包含"
DATASETS ||--o{ TRAINING_LOGS : "包含"
DATASETS ||--o{ DASHBOARD_CARDS : "包含"
DASHBOARDS ||--o{ DASHBOARD_CARDS : "包含"
```

### 典型查询示例

1. **获取用户的所有数据集**
   ```sql
   SELECT * FROM datasets WHERE owner_id = ? OR owner_id IS NULL;
   ```

2. **查询特定数据源的数据集**
   ```sql
   SELECT d.*, ds.name as datasource_name 
   FROM datasets d 
   JOIN datasources ds ON d.datasource_id = ds.id 
   WHERE ds.id = ?;
   ```

3. **统计用户数据集数量**
   ```sql
   SELECT COUNT(*) as count, status 
   FROM datasets 
   WHERE owner_id = ? 
   GROUP BY status;
   ```

4. **获取仪表板及其卡片**
   ```sql
   SELECT d.*, dc.title, dc.sql, dc.chart_type
   FROM dashboards d 
   LEFT JOIN dashboard_cards dc ON d.id = dc.dashboard_id
   WHERE d.id = ?;
   ```

**章节来源**
- [metadata.py](file://backend/app/models/metadata.py#L1-L129)
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L64-L97)