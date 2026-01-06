# SaaS 核心升级 - 数据模型与隔离机制使用指南

## 📋 升级概述

本次升级将系统改造为完整的 SaaS 多租户架构，实现了数据隔离和权限管理。

### 主要变更

1. **User 模型增强**
   - 新增 `is_superuser`：标识平台超级管理员
   - 新增 `is_deleted`：软删除标记

2. **业务模型增强**
   - 所有业务模型新增 `owner_id` 字段（可为 NULL）
   - `owner_id = NULL` 表示系统公共资源

3. **数据隔离机制**
   - 普通用户：只能访问自己的数据和公共资源
   - 超级管理员：可以访问所有数据

## 🗄️ 数据库迁移

### 方式一：使用 SQL 脚本（推荐）

```bash
# 对于 PostgreSQL
psql -U your_user -d your_database -f backend/migrations/001_add_saas_features.sql

# 对于 SQLite（参考脚本中的注释部分）
sqlite3 your_database.db < backend/migrations/001_add_saas_features.sql
```

### 方式二：使用 Alembic（未来可选）

如果使用 Alembic，可以根据模型变更生成迁移文件：

```bash
cd backend
alembic revision --autogenerate -m "Add SaaS features"
alembic upgrade head
```

### ⚠️ 重要提示

迁移脚本会将现有数据的 `owner_id` 设置为 1（假设 ID=1 是首个管理员）。
请根据实际情况调整迁移脚本中的 `owner_id` 值。

## 🔧 核心功能说明

### 1. 权限控制

#### 超级管理员
- 可以查看、修改、删除所有数据
- 可以创建公共资源（需手动设置 `owner_id=None`）
- 可以训练公共数据集

#### 普通用户
- 只能查看自己的数据和公共资源
- 不能修改或删除公共资源
- 不能训练公共数据集

### 2. 数据访问逻辑

所有 CRUD 操作都应用了 `apply_ownership_filter` 函数：

```python
from app.api.deps import apply_ownership_filter

# 查询示例
query = db.query(Dataset)
query = apply_ownership_filter(query, Dataset, current_user)
datasets = query.all()
```

过滤逻辑：
- 超级管理员：不过滤，返回所有数据
- 普通用户：只返回 `owner_id == current_user.id OR owner_id IS NULL` 的数据

### 3. 创建资源

所有新创建的资源自动设置 `owner_id = current_user.id`：

```python
# DataSource 创建示例
db_obj = DataSource(
    name=ds_in.name,
    type=ds_in.type,
    # ...
    owner_id=current_user.id  # 自动设置为当前用户
)
```

### 4. 公共资源管理

#### 创建公共资源（仅超级管理员）

目前暂不开放通过 API 创建公共资源，可通过数据库手动设置：

```sql
-- 将某个数据源设为公共资源
UPDATE datasources SET owner_id = NULL WHERE id = 1;

-- 将某个数据集设为公共资源
UPDATE datasets SET owner_id = NULL WHERE id = 1;
```

#### 修改/删除公共资源

所有 endpoint 都包含公共资源保护逻辑：

```python
# 额外检查：公共资源只有超级管理员可以修改
if dataset.owner_id is None and not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Cannot modify public resources")
```

## 📝 已更新的 Endpoint

### DataSource (datasource.py)
- ✅ `GET /datasources/` - 列表查询（应用隔离）
- ✅ `POST /datasources/` - 创建（自动设置 owner_id）
- ✅ `DELETE /datasources/{id}` - 删除（应用隔离 + 公共资源保护）
- ✅ `GET /datasources/{id}/tables` - 查询表（应用隔离）
- ✅ `GET /datasources/{id}/tables/{table_name}/preview` - 数据预览（应用隔离）

### Dataset (dataset.py)
- ✅ `GET /datasets/` - 列表查询（应用隔离）
- ✅ `POST /datasets/` - 创建（自动设置 owner_id + 验证 DataSource 权限）
- ✅ `PUT /datasets/{id}/tables` - 更新表配置（应用隔离 + 公共资源保护）
- ✅ `POST /datasets/{id}/train` - 训练数据集（应用隔离 + 公共资源保护）
- ✅ `POST /datasets/{id}/terms` - 添加业务术语（应用隔离 + 公共资源保护）
- ✅ `GET /datasets/{id}/terms` - 查询业务术语（应用隔离）
- ✅ `DELETE /datasets/terms/{term_id}` - 删除业务术语（应用隔离 + 公共资源保护）

### Dashboard (dashboard.py)
- ✅ `GET /dashboards/` - 列表查询（应用隔离）
- ✅ `POST /dashboards/` - 创建（自动设置 owner_id）
- ✅ `GET /dashboards/{id}` - 详情查询（应用隔离）
- ✅ `POST /dashboards/{id}/cards` - 添加卡片（应用隔离 + 公共资源保护）
- ✅ `DELETE /dashboards/cards/{id}` - 删除卡片（应用隔离 + 公共资源保护）
- ✅ `DELETE /dashboards/{id}` - 删除看板（应用隔离 + 公共资源保护）

### Chat (chat.py)
- ✅ `POST /chat/` - 对话查询（验证 Dataset 访问权限）
- ✅ `POST /chat/feedback` - 提交反馈（验证 Dataset 访问权限 + 公共资源保护）

## 🚀 使用示例

### 1. 创建超级管理员

```python
# 在数据库中设置
UPDATE users SET is_superuser = TRUE WHERE id = 1;

# 或在注册时通过代码设置（需要特殊逻辑）
user = User(
    email="admin@example.com",
    hashed_password=hash_password("password"),
    full_name="Admin",
    is_superuser=True
)
```

### 2. 普通用户访问数据

```python
# 普通用户登录后
# GET /api/v1/datasources/
# 返回：用户自己的数据源 + 公共数据源

# GET /api/v1/datasets/
# 返回：用户自己的数据集 + 公共数据集
```

### 3. 超级管理员管理公共资源

```sql
-- 创建公共数据源（通过 API 创建后手动设置）
-- 1. 通过 API 创建数据源（owner_id 自动设为管理员）
-- 2. 手动更新为公共资源
UPDATE datasources SET owner_id = NULL WHERE id = 10;

-- 现在所有用户都可以看到这个数据源，但只有超级管理员可以修改
```

### 4. 数据隔离验证

```bash
# 用户 A 创建数据源
curl -X POST http://localhost:8000/api/v1/datasources/ \
  -H "Authorization: Bearer <user_a_token>" \
  -d '{"name": "A的数据源", ...}'

# 用户 B 尝试访问
curl -X GET http://localhost:8000/api/v1/datasources/1 \
  -H "Authorization: Bearer <user_b_token>"
# 返回：404 Not found or access denied
```

## 🔒 安全注意事项

1. **软删除**：使用 `is_deleted` 标记删除用户，而不是物理删除，保护数据完整性
2. **权限检查**：所有涉及修改/删除的操作都包含公共资源保护逻辑
3. **数据隔离**：所有查询操作都应用了 `apply_ownership_filter`
4. **访问控制**：需要验证关联资源的访问权限（如创建 Dataset 时验证 DataSource）

## 📊 数据模型关系

```
User (用户)
├── is_superuser: 超级管理员标记
├── is_deleted: 软删除标记
│
├── DataSource (数据源)
│   └── owner_id: User.id (可为 NULL)
│
├── Dataset (数据集)
│   ├── owner_id: User.id (可为 NULL)
│   └── datasource_id: DataSource.id
│
├── Dashboard (仪表盘)
│   └── owner_id: User.id (可为 NULL)
│
├── BusinessTerm (业务术语)
│   ├── owner_id: User.id (可为 NULL)
│   └── dataset_id: Dataset.id
│
└── ChatMessage (聊天记录)
    ├── owner_id: User.id (可为 NULL)
    ├── user_id: User.id
    └── dataset_id: Dataset.id
```

## 🐛 故障排查

### 问题：用户无法看到任何数据

**原因**：现有数据的 `owner_id` 可能未正确设置

**解决**：
```sql
-- 检查数据分布
SELECT 'datasources' as table_name, 
       COUNT(*) as total, 
       COUNT(owner_id) as with_owner 
FROM datasources;

-- 如果需要，批量设置 owner_id
UPDATE datasources SET owner_id = 1 WHERE owner_id IS NULL;
```

### 问题：普通用户可以修改公共资源

**原因**：endpoint 可能缺少公共资源保护逻辑

**解决**：确保所有修改/删除操作都包含以下检查：
```python
if resource.owner_id is None and not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Cannot modify public resources")
```

## 📚 下一步优化建议

1. **前端适配**：更新前端代码，支持超级管理员界面
2. **公共资源管理**：添加超级管理员专用的公共资源管理 API
3. **审计日志**：记录所有数据访问和修改操作
4. **团队协作**：扩展为支持团队和组织级别的权限管理
5. **资源配额**：为不同用户设置资源使用配额

## 🎯 关键代码片段参考

### deps.py - 核心依赖函数

```python
def apply_ownership_filter(query, model, current_user: User):
    """应用数据隔离过滤逻辑"""
    if current_user.is_superuser:
        return query  # 超级管理员可以查看所有数据
    
    # 普通用户：只能查看自己的数据或公共资源
    return query.filter(
        or_(
            model.owner_id == current_user.id,
            model.owner_id.is_(None)
        )
    )
```

### endpoint 标准模式

```python
# 查询（列表）
@router.get("/", response_model=List[ResourceResponse])
def list_resources(db: Session = Depends(get_db), 
                   current_user: User = Depends(get_current_user)):
    query = db.query(Resource)
    query = apply_ownership_filter(query, Resource, current_user)
    return query.all()

# 创建
@router.post("/", response_model=ResourceResponse)
def create_resource(resource_in: ResourceCreate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    resource = Resource(
        name=resource_in.name,
        owner_id=current_user.id  # 自动设置
    )
    db.add(resource)
    db.commit()
    return resource

# 删除
@router.delete("/{id}")
def delete_resource(id: int,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    query = db.query(Resource).filter(Resource.id == id)
    query = apply_ownership_filter(query, Resource, current_user)
    resource = query.first()
    
    if not resource:
        raise HTTPException(status_code=404, detail="Not found or access denied")
    
    # 公共资源保护
    if resource.owner_id is None and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete public resources")
    
    db.delete(resource)
    db.commit()
    return {"message": "Deleted successfully"}
```

---

**版本**: 1.0.0  
**更新时间**: 2026-01-06  
**作者**: AI Assistant
