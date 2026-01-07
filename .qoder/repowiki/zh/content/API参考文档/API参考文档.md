# API参考文档

<cite>
**本文档中引用的文件**
- [main.py](file://backend/app/main.py)
- [auth.py](file://backend/app/api/v1/endpoints/auth.py)
- [admin.py](file://backend/app/api/v1/endpoints/admin.py)
- [chat.py](file://backend/app/api/v1/endpoints/chat.py)
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py)
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py)
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py)
- [token.py](file://backend/app/schemas/token.py)
- [user.py](file://backend/app/schemas/user.py)
- [datasource.py](file://backend/app/schemas/datasource.py)
- [dataset.py](file://backend/app/schemas/dataset.py)
- [chat.py](file://backend/app/schemas/chat.py)
- [dashboard.py](file://backend/app/schemas/dashboard.py)
- [deps.py](file://backend/app/api/deps.py)
- [security.py](file://backend/app/core/security.py)
- [chat.ts](file://frontend/src/api/chat.ts)
- [datasource.ts](file://frontend/src/api/datasource.ts)
- [dataset.ts](file://frontend/src/api/dataset.ts)
- [dashboard.ts](file://frontend/src/api/dashboard.ts)
- [user.ts](file://frontend/src/api/user.ts)
</cite>

## 目录
1. [简介](#简介)
2. [认证机制](#认证机制)
3. [通用查询参数](#通用查询参数)
4. [认证接口](#认证接口)
5. [管理员接口](#管理员接口)
6. [数据源接口](#数据源接口)
7. [数据集接口](#数据集接口)
8. [聊天接口](#聊天接口)
9. [看板接口](#看板接口)

## 简介

本API参考文档详细描述了Universal BI系统的RESTful接口。所有API端点均基于FastAPI框架构建，遵循OpenAPI规范。API基础路径为`/api/v1`，所有接口均需通过Bearer Token进行认证。

系统主要功能模块包括：
- 用户认证与管理
- 数据源连接与管理
- 数据集创建与训练
- 自然语言聊天查询
- 看板与数据可视化

前端通过TypeScript调用这些API，确保接口使用的一致性和准确性。

**本文档中引用的文件**
- [main.py](file://backend/app/main.py#L11-L30)

## 认证机制

所有需要认证的API接口均使用Bearer Token机制。用户首先通过`/api/v1/auth/login`接口获取访问令牌，然后在后续请求的`Authorization`头部中包含该令牌。

### 认证流程

1. **登录获取Token**：用户通过邮箱和密码登录，成功后返回JWT格式的访问令牌。
2. **携带Token请求**：在请求头部添加`Authorization: Bearer <access_token>`。
3. **Token验证**：服务器验证Token的有效性、签名和过期时间。
4. **Token注销**：用户登出时，Token将被加入Redis黑名单，防止继续使用。

### 安全检查

系统在认证过程中执行多项安全检查：
- Token是否在黑名单中（已注销）
- Token签名是否有效
- 用户账户是否被删除（`is_deleted`）
- 用户账户是否被封禁（`is_active`）
- 用户是否为超级管理员（`is_superuser`）

Token有效期由`ACCESS_TOKEN_EXPIRE_MINUTES`配置项决定，默认为30分钟。

**本文档中引用的文件**
- [auth.py](file://backend/app/api/v1/endpoints/auth.py#L17-L146)
- [deps.py](file://backend/app/api/deps.py#L17-L80)
- [security.py](file://backend/app/core/security.py#L73-L80)

## 通用查询参数

多个API接口支持通用的分页和过滤查询参数，以提高数据检索的灵活性。

### 分页参数

| 参数 | 类型 | 必需 | 描述 | 默认值 | 约束 |
|------|------|------|------|--------|------|
| `page` | 整数 | 否 | 页码，从1开始 | 1 | ≥1 |
| `page_size` | 整数 | 否 | 每页数量 | 20 | 1-100 |

### 过滤参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `search` | 字符串 | 否 | 搜索关键词，支持按邮箱或全名模糊匹配 |

### 数据隔离

系统实现了严格的数据隔离机制，确保用户只能访问自己的数据或公共资源：
- 普通用户：只能查看`owner_id`等于自己ID或`owner_id`为NULL的数据
- 超级管理员：可以查看所有数据

此逻辑通过`apply_ownership_filter`函数实现，在查询数据库时自动应用过滤条件。

**本文档中引用的文件**
- [admin.py](file://backend/app/api/v1/endpoints/admin.py#L20-L22)
- [deps.py](file://backend/app/api/deps.py#L97-L123)

## 认证接口

认证接口提供用户注册、登录、登出和获取用户信息的功能。

### POST /api/v1/auth/register - 用户注册

创建新用户账户。

**请求体 (application/json)**
```json
{
  "email": "string",
  "password": "string",
  "full_name": "string"
}
```

**响应模型**
- `200 OK`: 返回`UserOut`模型
- `400 Bad Request`: 邮箱已注册

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "full_name": "张三"
  }'
```

```javascript
fetch('/api/v1/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    full_name: '张三'
  })
})
```

**本文档中引用的文件**
- [auth.py](file://backend/app/api/v1/endpoints/auth.py#L57-L98)

### POST /api/v1/auth/login - 用户登录

获取访问令牌。

**请求体 (application/x-www-form-urlencoded)**
- `username`: 用户邮箱
- `password`: 用户密码

**响应模型**
- `200 OK`: 返回`Token`模型
- `400 Bad Request`: 邮箱未注册或密码错误
- `400 Bad Request`: 账号被禁用

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"
```

```javascript
const formData = new FormData();
formData.append('username', 'user@example.com');
formData.append('password', 'password123');

fetch('/api/v1/auth/login', {
  method: 'POST',
  body: formData
})
```

**本文档中引用的文件**
- [auth.py](file://backend/app/api/v1/endpoints/auth.py#L17-L55)

### POST /api/v1/auth/logout - 用户登出

将Token加入黑名单，实现登出功能。

**请求头**
- `Authorization: Bearer <access_token>`

**响应**
- `200 OK`: 登出成功
- `401 Unauthorized`: Token无效

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/auth/logout', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [auth.py](file://backend/app/api/v1/endpoints/auth.py#L101-L133)

### GET /api/v1/auth/me - 获取当前用户信息

获取当前登录用户的详细信息。

**请求头**
- `Authorization: Bearer <access_token>`

**响应模型**
- `200 OK`: 返回`User`模型
- `401 Unauthorized`: Token无效或已注销

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/auth/me', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [auth.py](file://backend/app/api/v1/endpoints/auth.py#L136-L146)

## 管理员接口

管理员接口仅限超级管理员使用，提供用户管理功能。

### GET /api/v1/admin/users - 获取用户列表

获取分页的用户列表，支持搜索。

**请求头**
- `Authorization: Bearer <access_token>`

**查询参数**
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）
- `search`: 搜索关键词

**响应模型**
- `200 OK`: 返回`UsersListResponse`模型
- `403 Forbidden`: 权限不足

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?page=1&page_size=10&search=张" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/admin/users?page=1&page_size=10&search=张', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [admin.py](file://backend/app/api/v1/endpoints/admin.py#L16-L60)

### PATCH /api/v1/admin/users/{user_id}/status - 修改用户状态

封禁或解封用户账户。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `user_id`: 用户ID

**请求体**
```json
{
  "is_active": false
}
```

**响应模型**
- `200 OK`: 返回`UserListOut`模型
- `403 Forbidden`: 不能修改自己的状态
- `404 Not Found`: 用户不存在

**调用示例**
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/1/status" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

```javascript
fetch('/api/v1/admin/users/1/status', {
  method: 'PATCH',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({is_active: false})
})
```

**本文档中引用的文件**
- [admin.py](file://backend/app/api/v1/endpoints/admin.py#L63-L107)

### DELETE /api/v1/admin/users/{user_id} - 软删除用户

软删除用户账户。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `user_id`: 用户ID

**响应模型**
- `200 OK`: 返回`UserListOut`模型
- `403 Forbidden`: 不能删除自己的账户
- `404 Not Found`: 用户不存在

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/users/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/admin/users/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [admin.py](file://backend/app/api/v1/endpoints/admin.py#L110-L159)

### PATCH /api/v1/admin/users/{user_id} - 修改用户信息

修改用户信息，仅用于紧急维护。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `user_id`: 用户ID

**请求体**
```json
{
  "full_name": "新昵称",
  "password": "新密码",
  "role": "admin"
}
```

**响应模型**
- `200 OK`: 返回`UserListOut`模型
- `400 Bad Request`: 未提供更新字段
- `403 Forbidden`: 不能修改自己的信息

**调用示例**
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/1" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "新昵称",
    "password": "新密码123"
  }'
```

```javascript
fetch('/api/v1/admin/users/1', {
  method: 'PATCH',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    full_name: '新昵称',
    password: '新密码123'
  })
})
```

**本文档中引用的文件**
- [admin.py](file://backend/app/api/v1/endpoints/admin.py#L162-L231)

## 数据源接口

数据源接口管理数据库连接信息。

### POST /api/v1/datasources/test - 测试数据源连接

测试数据源连接而不保存。

**请求体**
```json
{
  "name": "测试数据源",
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "username": "user",
  "password": "password",
  "database_name": "testdb"
}
```

**响应**
- `200 OK`: 返回布尔值，true表示连接成功

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasources/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "测试数据源",
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "username": "user",
    "password": "password",
    "database_name": "testdb"
  }'
```

```javascript
fetch('/api/v1/datasources/test', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '测试数据源',
    type: 'postgresql',
    host: 'localhost',
    port: 5432,
    username: 'user',
    password: 'password',
    database_name: 'testdb'
  })
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L20-L29)

### POST /api/v1/datasources - 创建数据源

创建新的数据源。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "name": "生产数据库",
  "type": "mysql",
  "host": "prod.example.com",
  "port": 3306,
  "username": "admin",
  "password": "secret",
  "database_name": "production"
}
```

**响应模型**
- `200 OK`: 返回`DataSource`模型
- `400 Bad Request`: 名称已存在

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasources" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "生产数据库",
    "type": "mysql",
    "host": "prod.example.com",
    "port": 3306,
    "username": "admin",
    "password": "secret",
    "database_name": "production"
  }'
```

```javascript
fetch('/api/v1/datasources', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '生产数据库',
    type: 'mysql',
    host: 'prod.example.com',
    port: 3306,
    username: 'admin',
    password: 'secret',
    database_name: 'production'
  })
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L31-L58)

### GET /api/v1/datasources - 获取数据源列表

获取数据源列表。

**请求头**
- `Authorization: Bearer <access_token>`

**查询参数**
- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的最大记录数（默认100）

**响应模型**
- `200 OK`: 返回`DataSource`模型数组
- `401 Unauthorized`: 未认证

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasources?skip=0&limit=10" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasources?skip=0&limit=10', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L60-L74)

### DELETE /api/v1/datasources/{id} - 删除数据源

删除指定ID的数据源。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据源ID

**响应**
- `200 OK`: 返回true
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/datasources/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasources/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L76-L99)

### GET /api/v1/datasources/{id}/tables - 获取数据源表结构

获取数据源中所有表的结构信息。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据源ID

**响应模型**
- `200 OK`: 返回`TableInfo`模型数组
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasources/1/tables" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasources/1/tables', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L101-L155)

### GET /api/v1/datasources/{id}/tables/{table_name}/preview - 预览表数据

预览指定表的前几行数据。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据源ID
- `table_name`: 表名

**响应**
- `200 OK`: 返回包含列名和数据行的对象
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasources/1/tables/users/preview" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasources/1/tables/users/preview', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [datasource.py](file://backend/app/api/v1/endpoints/datasource.py#L160-L181)

## 数据集接口

数据集接口管理数据集的创建、训练和业务术语。

### POST /api/v1/datasets - 创建数据集

创建新的数据集。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "name": "销售数据集",
  "datasource_id": 1
}
```

**响应模型**
- `200 OK`: 返回`DatasetResponse`模型
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "销售数据集",
    "datasource_id": 1
  }'
```

```javascript
fetch('/api/v1/datasets', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '销售数据集',
    datasource_id: 1
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L29-L62)

### GET /api/v1/datasets - 获取数据集列表

获取数据集列表。

**请求头**
- `Authorization: Bearer <access_token>`

**查询参数**
- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的最大记录数（默认100）

**响应模型**
- `200 OK`: 返回`DatasetResponse`模型数组
- `401 Unauthorized`: 未认证

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets?skip=0&limit=10" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets?skip=0&limit=10', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L64-L77)

### GET /api/v1/datasets/{id} - 获取数据集详情

获取指定ID的数据集详情。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应模型**
- `200 OK`: 返回`DatasetResponse`模型
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L80-L97)

### PUT /api/v1/datasets/{id}/tables - 更新数据集表配置

更新数据集的表配置。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**请求体**
```json
{
  "schema_config": ["users", "orders", "products"]
}
```

**响应模型**
- `200 OK`: 返回`DatasetResponse`模型
- `403 Forbidden`: 不能修改公共资源
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X PUT "http://localhost:8000/api/v1/datasets/1/tables" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "schema_config": ["users", "orders", "products"]
  }'
```

```javascript
fetch('/api/v1/datasets/1/tables', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    schema_config: ['users', 'orders', 'products']
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L99-L124)

### POST /api/v1/datasets/{id}/train - 触发数据集训练

触发数据集的AI训练过程。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应**
- `200 OK`: 返回{"message": "训练已开始"}
- `400 Bad Request`: 未选择训练表
- `403 Forbidden`: 不能训练公共资源
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/1/train" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/train', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L126-L167)

### POST /api/v1/datasets/{id}/terms - 添加业务术语

为数据集添加业务术语并训练AI。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**请求体**
```json
{
  "term": "GMV",
  "definition": "商品交易总额，指所有订单的总金额"
}
```

**响应模型**
- `200 OK`: 返回`BusinessTermResponse`模型
- `403 Forbidden`: 不能为公共资源添加术语
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/1/terms" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "term": "GMV",
    "definition": "商品交易总额，指所有订单的总金额"
  }'
```

```javascript
fetch('/api/v1/datasets/1/terms', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    term: 'GMV',
    definition: '商品交易总额，指所有订单的总金额'
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L170-L219)

### GET /api/v1/datasets/{id}/terms - 获取业务术语列表

获取数据集的所有业务术语。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应模型**
- `200 OK`: 返回`BusinessTermResponse`模型数组
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/1/terms" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/terms', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L222-L245)

### DELETE /api/v1/datasets/terms/{term_id} - 删除业务术语

删除指定ID的业务术语。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `term_id`: 术语ID

**响应**
- `200 OK`: 返回{"message": "术语已删除（注：向量库中的训练数据仍保留）"}
- `403 Forbidden`: 不能删除公共资源
- `404 Not Found`: 术语不存在或无权访问

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/datasets/terms/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/terms/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L248-L274)

### POST /api/v1/datasets/analyze - 分析表关系

使用AI分析表之间的潜在关系。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "datasource_id": 1,
  "table_names": ["users", "orders"]
}
```

**响应模型**
- `200 OK`: 返回`AnalyzeRelationshipsResponse`模型
- `400 Bad Request`: 至少需要一个表名
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "datasource_id": 1,
    "table_names": ["users", "orders"]
  }'
```

```javascript
fetch('/api/v1/datasets/analyze', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    datasource_id: 1,
    table_names: ['users', 'orders']
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L278-L329)

### POST /api/v1/datasets/create_view - 创建数据库视图

创建或替换数据库视图。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "datasource_id": 1,
  "view_name": "sales_summary",
  "sql": "SELECT user_id, SUM(amount) as total FROM orders GROUP BY user_id"
}
```

**响应**
- `200 OK`: 返回{"message": "视图 sales_summary 创建成功", "view_name": "sales_summary"}
- `400 Bad Request`: 视图名无效或SQL不是SELECT查询
- `403 Forbidden`: 不能在公共数据源上创建视图
- `404 Not Found`: 数据源不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/create_view" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "datasource_id": 1,
    "view_name": "sales_summary",
    "sql": "SELECT user_id, SUM(amount) as total FROM orders GROUP BY user_id"
  }'
```

```javascript
fetch('/api/v1/datasets/create_view', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    datasource_id: 1,
    view_name: 'sales_summary',
    sql: 'SELECT user_id, SUM(amount) as total FROM orders GROUP BY user_id'
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L515-L597)

### GET /api/v1/datasets/{id}/training/progress - 获取训练进度

获取数据集的训练进度。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应**
- `200 OK`: 返回包含状态、进度率、错误信息和当前步骤的对象
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/1/training/progress" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/training/progress', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L602-L630)

### GET /api/v1/datasets/{id}/training/logs - 获取训练日志

获取数据集的训练日志。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**查询参数**
- `limit`: 返回的最大日志条数（默认50）

**响应模型**
- `200 OK`: 返回`TrainingLogResponse`模型数组
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/1/training/logs?limit=10" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/training/logs?limit=10', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L633-L656)

### GET /api/v1/datasets/{id}/training/data - 获取训练数据

获取已训练的数据（QA对、DDL、文档）。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**查询参数**
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）

**响应模型**
- `200 OK`: 返回`TrainingDataResponse`模型
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/1/training/data?page=1&page_size=10" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/training/data?page=1&page_size=10', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L659-L691)

### POST /api/v1/datasets/{id}/training/pause - 暂停训练

暂停正在进行的训练。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应**
- `200 OK`: 返回{"message": "训练暂停请求已发送"}
- `400 Bad Request`: 数据集未在训练中
- `403 Forbidden`: 不能暂停公共资源的训练
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/1/training/pause" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/training/pause', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L694-L720)

### DELETE /api/v1/datasets/{id}/training - 删除训练数据

删除数据集的训练数据（清理Collection）。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应**
- `200 OK`: 返回{"message": "训练数据已清理"}
- `403 Forbidden`: 不能删除公共资源的训练数据
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/datasets/1/training" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1/training', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L723-L749)

### DELETE /api/v1/datasets/{id} - 删除数据集

删除数据集及其相关数据。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**响应**
- `200 OK`: 返回{"message": "数据集已删除"}
- `403 Forbidden`: 不能删除公共资源
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/datasets/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/datasets/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L752-L785)

### PUT /api/v1/datasets/{id}/modeling-config - 更新建模配置

更新数据集的建模配置（保存画布数据）。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 数据集ID

**查询参数**
- `train_relationships`: 是否立即训练表关系（默认false）

**请求体**
```json
{
  "nodes": [
    {
      "id": "node-users",
      "data": {
        "label": "users"
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-users",
      "target": "node-orders",
      "sourceHandle": "id",
      "targetHandle": "user_id"
    }
  ]
}
```

**响应**
- `200 OK`: 返回更新后的数据集信息
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X PUT "http://localhost:8000/api/v1/datasets/1/modeling-config?train_relationships=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "nodes": [
      {
        "id": "node-users",
        "data": {
          "label": "users"
        }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-users",
        "target": "node-orders",
        "sourceHandle": "id",
        "targetHandle": "user_id"
      }
    ]
  }'
```

```javascript
fetch('/api/v1/datasets/1/modeling-config?train_relationships=true', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nodes: [{
      id: 'node-users',
      data: {label: 'users'}
    }],
    edges: [{
      id: 'edge-1',
      source: 'node-users',
      target: 'node-orders',
      sourceHandle: 'id',
      targetHandle: 'user_id'
    }]
  })
})
```

**本文档中引用的文件**
- [dataset.py](file://backend/app/api/v1/endpoints/dataset.py#L788-L800)

## 聊天接口

聊天接口提供自然语言查询和AI反馈功能。

### POST /api/v1/chat/ - 聊天查询

与数据集聊天以生成SQL和结果。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "dataset_id": 1,
  "question": "上个月销售额是多少？"
}
```

**响应模型**
- `200 OK`: 返回`ChatResponse`模型
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "dataset_id": 1,
    "question": "上个月销售额是多少？"
  }'
```

```javascript
fetch('/api/v1/chat/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    dataset_id: 1,
    question: '上个月销售额是多少？'
  })
})
```

**本文档中引用的文件**
- [chat.py](file://backend/app/api/v1/endpoints/chat.py#L13-L37)

### POST /api/v1/chat/feedback - 提交反馈

提交用户对AI生成SQL的反馈。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "dataset_id": 1,
  "question": "上个月销售额是多少？",
  "sql": "SELECT SUM(amount) FROM orders WHERE month = '2023-10'",
  "rating": 1
}
```

**响应模型**
- `200 OK`: 返回`FeedbackResponse`模型
- `400 Bad Request`: 无效的评分值
- `403 Forbidden`: 不能训练公共资源
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "dataset_id": 1,
    "question": "上个月销售额是多少？",
    "sql": "SELECT SUM(amount) FROM orders WHERE month = \"2023-10\"",
    "rating": 1
  }'
```

```javascript
fetch('/api/v1/chat/feedback', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    dataset_id: 1,
    question: '上个月销售额是多少？',
    sql: 'SELECT SUM(amount) FROM orders WHERE month = "2023-10"',
    rating: 1
  })
})
```

**本文档中引用的文件**
- [chat.py](file://backend/app/api/v1/endpoints/chat.py#L44-L111)

### POST /api/v1/chat/summary - 生成摘要

生成查询结果的AI业务摘要。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "dataset_id": 1,
  "question": "上个月销售额是多少？",
  "sql": "SELECT SUM(amount) FROM orders WHERE month = '2023-10'",
  "columns": ["sum"],
  "rows": [{"sum": 100000}]
}
```

**响应模型**
- `200 OK`: 返回`SummaryResponse`模型
- `404 Not Found`: 数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/summary" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "dataset_id": 1,
    "question": "上个月销售额是多少？",
    "sql": "SELECT SUM(amount) FROM orders WHERE month = \"2023-10\"",
    "columns": ["sum"],
    "rows": [{"sum": 100000}]
  }'
```

```javascript
fetch('/api/v1/chat/summary', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    dataset_id: 1,
    question: '上个月销售额是多少？',
    sql: 'SELECT SUM(amount) FROM orders WHERE month = "2023-10"',
    columns: ['sum'],
    rows: [{'sum': 100000}]
  })
})
```

**本文档中引用的文件**
- [chat.py](file://backend/app/api/v1/endpoints/chat.py#L113-L155)

## 看板接口

看板接口管理数据可视化看板。

### POST /api/v1/dashboards - 创建看板

创建新的空看板。

**请求头**
- `Authorization: Bearer <access_token>`

**请求体**
```json
{
  "name": "销售看板",
  "description": "月度销售数据可视化"
}
```

**响应模型**
- `200 OK`: 返回`DashboardResponse`模型
- `401 Unauthorized`: 未认证

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/dashboards" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "销售看板",
    "description": "月度销售数据可视化"
  }'
```

```javascript
fetch('/api/v1/dashboards', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '销售看板',
    description: '月度销售数据可视化'
  })
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L25-L43)

### GET /api/v1/dashboards - 获取看板列表

获取看板列表。

**请求头**
- `Authorization: Bearer <access_token>`

**查询参数**
- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的最大记录数（默认100）

**响应模型**
- `200 OK`: 返回`DashboardResponse`模型数组
- `401 Unauthorized`: 未认证

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards?skip=0&limit=10" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/dashboards?skip=0&limit=10', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L46-L60)

### GET /api/v1/dashboards/{id} - 获取看板详情

获取指定ID的看板详情。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 看板ID

**响应模型**
- `200 OK`: 返回`DashboardResponse`模型
- `404 Not Found`: 看板不存在或无权访问

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/dashboards/1', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L63-L79)

### POST /api/v1/dashboards/{id}/cards - 添加卡片

向看板添加卡片。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 看板ID

**请求体**
```json
{
  "title": "销售额趋势",
  "dataset_id": 1,
  "sql": "SELECT date, SUM(amount) FROM orders GROUP BY date",
  "chart_type": "line",
  "layout": {
    "x": 0,
    "y": 0,
    "w": 12,
    "h": 8
  }
}
```

**响应模型**
- `200 OK`: 返回`DashboardCardResponse`模型
- `403 Forbidden`: 不能修改公共资源
- `404 Not Found`: 看板或数据集不存在或无权访问

**调用示例**
```bash
curl -X POST "http://localhost:8000/api/v1/dashboards/1/cards" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "title": "销售额趋势",
    "dataset_id": 1,
    "sql": "SELECT date, SUM(amount) FROM orders GROUP BY date",
    "chart_type": "line",
    "layout": {
      "x": 0,
      "y": 0,
      "w": 12,
      "h": 8
    }
  }'
```

```javascript
fetch('/api/v1/dashboards/1/cards', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: '销售额趋势',
    dataset_id: 1,
    sql: 'SELECT date, SUM(amount) FROM orders GROUP BY date',
    chart_type: 'line',
    layout: {
      x: 0,
      y: 0,
      w: 12,
      h: 8
    }
  })
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L82-L129)

### GET /api/v1/dashboards/cards/{id}/data - 获取卡片数据

获取卡片的最新数据。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 卡片ID

**响应模型**
- `200 OK`: 返回`DashboardCardDataResponse`模型
- `400 Bad Request`: SQL执行错误
- `404 Not Found`: 卡片不存在

**调用示例**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards/cards/1/data" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/dashboards/cards/1/data', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L132-L197)

### DELETE /api/v1/dashboards/cards/{id} - 删除卡片

删除指定ID的卡片。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 卡片ID

**响应**
- `200 OK`: 返回{"message": "Card deleted successfully"}
- `403 Forbidden`: 不能修改公共资源
- `404 Not Found`: 卡片不存在

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/dashboards/cards/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/dashboards/cards/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L200-L234)

### DELETE /api/v1/dashboards/{id} - 删除看板

删除看板及其所有卡片。

**请求头**
- `Authorization: Bearer <access_token>`

**路径参数**
- `id`: 看板ID

**响应**
- `200 OK`: 返回{"message": "Dashboard deleted successfully"}
- `403 Forbidden`: 不能删除公共资源
- `404 Not Found`: 看板不存在或无权访问

**调用示例**
```bash
curl -X DELETE "http://localhost:8000/api/v1/dashboards/1" \
  -H "Authorization: Bearer <access_token>"
```

```javascript
fetch('/api/v1/dashboards/1', {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**本文档中引用的文件**
- [dashboard.py](file://backend/app/api/v1/endpoints/dashboard.py#L237-L260)