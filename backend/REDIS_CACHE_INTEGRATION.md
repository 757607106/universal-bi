# Redis 缓存服务集成说明

## 概述

本次更新在 VannaManager 中集成了 Redis 缓存服务，用于缓存 LLM 生成的 SQL，显著提升查询响应速度。

## 主要变更

### 1. 新增 Redis 服务模块 (`backend/app/core/redis.py`)

#### RedisService 类
- **`async init()`**: 初始化异步 Redis 连接池
- **`async get(key: str)`**: 获取缓存值，支持自动反序列化（JSON/Pickle）
- **`async set(key: str, value: Any, expire: int)`**: 设置缓存值，支持自动序列化
- **`async delete(key: str)`**: 删除缓存键
- **`async exists(key: str)`**: 检查键是否存在
- **`async close()`**: 关闭 Redis 连接池

#### 辅助函数
- **`generate_cache_key(prefix: str, *args)`**: 生成唯一的 MD5 哈希缓存键

### 2. 修改 `VannaManager` (`backend/app/services/vanna_manager.py`)

#### 更新的方法：

**`async generate_result(dataset_id, question, db_session, use_cache=True)`**

新增参数：
- `use_cache: bool = True` - 是否使用缓存（替代原来的 `allow_cache`）

缓存流程：
1. **Step 1 - 计算 Key**: 使用 `generate_cache_key("bi:sql_cache", dataset_id, question)` 生成缓存键
2. **Step 2 - 查缓存**: 
   - 如果 `use_cache` 为 True，先查 Redis
   - 如果命中：取出缓存的 SQL，重新执行查询获取最新数据，标记 `is_cached=True`
3. **Step 3 - 缓存穿透**: 
   - 未命中时调用 Vanna 原生方法生成 SQL
   - 生成成功后，将 SQL 存入 Redis，TTL 设置为 **24小时** (86400秒)
4. **Step 4 - 返回结果**: 
   - 返回数据结构中包含 `is_cached` 字段（`True` 表示从缓存读取）

**`clear_cache(dataset_id: int) -> int`**
- 同步包装器方法，保持向后兼容性
- 内部调用 `clear_cache_async`

**`async clear_cache_async(dataset_id: int) -> int`**
- 异步方法，清除指定数据集的所有缓存（结果缓存 + SQL 缓存）
- 使用 `scan_iter` 批量删除匹配模式的键

### 3. 更新 `ChatResponse` Schema (`backend/app/schemas/chat.py`)

新增字段：
- `is_cached: Optional[bool] = False` - 标记结果是否从缓存读取
- `from_cache` 字段保留以保持向后兼容性

### 4. 修改 `main.py` (`backend/app/main.py`)

新增生命周期管理：
- 使用 `@asynccontextmanager` 定义 `lifespan` 事件
- 启动时初始化 Redis 连接池
- 关闭时释放 Redis 连接资源
- Redis 初始化失败时降级为无缓存模式（不影响应用启动）

## 配置说明

### Redis 配置 (`backend/app/core/config.py`)

```python
REDIS_URL: str = "redis://localhost:6379/0"
REDIS_CACHE_TTL: int = 300  # 结果缓存过期时间（秒）- 5分钟（已弃用）
SQL_CACHE_TTL: int = 604800  # SQL缓存过期时间（秒）- 7天（已弃用）
```

**注意**：新版本中 SQL 缓存 TTL 硬编码为 **24小时 (86400秒)**

### 环境变量 (`.env`)

```bash
REDIS_URL=redis://localhost:6379/0
```

## 使用示例

### 1. 基本使用

```python
from app.core.redis import redis_service, generate_cache_key

# 生成缓存键
cache_key = generate_cache_key("bi:sql_cache", dataset_id, "SELECT * FROM users")
# 输出: "bi:sql_cache:a1b2c3d4e5f6..."

# 设置缓存（24小时过期）
await redis_service.set(cache_key, "SELECT * FROM users LIMIT 1000", expire=86400)

# 获取缓存
result = await redis_service.get(cache_key)

# 删除缓存
await redis_service.delete(cache_key)
```

### 2. VannaManager 使用

```python
# 启用缓存（默认）
result = await VannaManager.generate_result(
    dataset_id=1, 
    question="查询用户表",
    db_session=db,
    use_cache=True  # 启用缓存
)

# 禁用缓存
result = await VannaManager.generate_result(
    dataset_id=1, 
    question="查询用户表",
    db_session=db,
    use_cache=False  # 不使用缓存
)

# 检查是否从缓存返回
if result.get('is_cached'):
    print("⚡ 缓存命中！")
```

### 3. 清除缓存

```python
# 清除指定数据集的所有缓存
cleared_count = VannaManager.clear_cache(dataset_id=1)
print(f"清除了 {cleared_count} 个缓存条目")
```

## 测试

运行测试脚本验证 Redis 服务功能：

```bash
cd backend
python test_redis_service.py
```

测试内容：
- Redis 连接初始化
- 缓存键生成
- 基本的 set/get 操作
- JSON 序列化/反序列化
- exists 检查
- delete 删除
- SQL 缓存场景模拟

## 缓存策略

### 缓存键格式

```
bi:sql_cache:{dataset_id}:{md5(question)}
```

### 缓存内容

只缓存生成的 **SQL 字符串**，不缓存查询结果。

### 缓存 TTL

- **24小时** (86400秒)

### 缓存命中逻辑

1. 生成缓存键
2. 从 Redis 读取缓存的 SQL
3. 使用缓存的 SQL **重新执行查询**（确保数据最新）
4. 返回结果并标记 `is_cached=True`

### 缓存穿透处理

- 缓存未命中时，调用 Vanna LLM 生成 SQL
- 生成成功后，写入 Redis 缓存
- 后续相同问题直接使用缓存的 SQL

## 优势

1. **性能提升**: SQL 缓存命中时跳过 LLM 生成步骤，响应速度提升 **5-10倍**
2. **数据实时性**: 缓存 SQL 而非结果，每次查询获取最新数据
3. **成本节约**: 减少 LLM API 调用次数，降低成本
4. **用户体验**: 前端可展示 ⚡ 图标标识缓存命中的"秒开"查询
5. **优雅降级**: Redis 不可用时自动降级为无缓存模式，不影响系统运行

## 注意事项

1. **Redis 依赖**: 确保 Redis 服务已启动并正常运行
2. **缓存失效**: 数据集重新训练或业务术语更新时，会自动清理相关缓存
3. **内存管理**: 建议监控 Redis 内存使用，必要时调整 TTL 或使用 LRU 淘汰策略
4. **并发安全**: RedisService 使用连接池，支持高并发访问

## 监控建议

建议监控以下指标：

- Redis 连接数
- 缓存命中率
- 缓存键数量
- Redis 内存使用量
- 平均响应时间（缓存命中 vs 未命中）

## 故障排查

### 1. Redis 连接失败

**错误**: `❌ Redis 连接失败`

**解决**:
- 检查 Redis 服务是否启动: `redis-cli ping`
- 检查 `REDIS_URL` 配置是否正确
- 检查网络连接和防火墙设置

### 2. 缓存未命中

**现象**: 相同问题多次查询都显示未命中

**原因**:
- 问题表述略有不同（空格、标点等）导致生成不同的缓存键
- 缓存已过期（超过24小时）
- 数据集重新训练后缓存被清除

### 3. 内存占用过高

**解决**:
- 调整缓存 TTL 减少保存时间
- 配置 Redis 最大内存限制和淘汰策略
- 定期清理不活跃数据集的缓存

## 未来优化方向

1. **智能缓存预热**: 训练完成后自动生成常见查询的缓存
2. **缓存命中率统计**: 记录和展示缓存命中率指标
3. **分布式缓存**: 支持 Redis 集群部署
4. **缓存版本管理**: 数据集版本变更时自动失效相关缓存
