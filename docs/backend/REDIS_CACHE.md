# Redis 缓存功能说明

## 概述

为了提升智能问答系统的响应速度，我们基于 Redis 实现了查询结果缓存。该功能具有以下特点：

- ✅ **智能缓存**: 自动缓存成功的查询结果
- ✅ **快速响应**: 命中缓存时可秒级返回结果
- ✅ **自动过期**: 默认 5 分钟 TTL，避免过期数据
- ✅ **异常降级**: Redis 不可用时自动降级，不影响核心功能
- ✅ **自动清理**: 数据集重新训练或更新术语时自动清除相关缓存

## 配置

### 1. 安装 Redis 依赖

```bash
pip install redis>=5.0.0
```

### 2. 配置环境变量

在 `.env` 文件或环境变量中配置：

```bash
# Redis 连接 URL
REDIS_URL=redis://localhost:6379/0

# 缓存过期时间（秒），默认 300 秒（5 分钟）
REDIS_CACHE_TTL=300
```

### 3. 启动 Redis

使用 Docker：
```bash
docker run -d -p 6379:6379 redis
```

或使用本地安装：
```bash
# macOS
brew install redis
redis-server

# Ubuntu
sudo apt-get install redis
sudo service redis start
```

## 使用方式

### 1. 基本使用

缓存功能已集成到 `VannaManager.generate_result()` 中，默认自动启用：

```python
from app.services.vanna_manager import VannaManager

# 第一次查询 - 执行 SQL 并缓存结果
result1 = await VannaManager.generate_result(
    dataset_id=1,
    question="查询销售数据",
    db_session=db
)
# result1['from_cache'] = False

# 第二次相同查询 - 直接从缓存返回
result2 = await VannaManager.generate_result(
    dataset_id=1,
    question="查询销售数据",
    db_session=db
)
# result2['from_cache'] = True
```

### 2. 禁用缓存

某些场景下可能需要跳过缓存，直接获取最新数据：

```python
result = await VannaManager.generate_result(
    dataset_id=1,
    question="查询实时数据",
    db_session=db,
    allow_cache=False  # 禁用缓存
)
```

### 3. 清除缓存

在以下场景需要清除缓存：

- 数据集重新训练后（已自动处理）
- 添加/更新业务术语后（已自动处理）
- 手动刷新数据后

```python
# 清除指定数据集的所有缓存
cleared_count = VannaManager.clear_cache(dataset_id=1)
print(f"已清除 {cleared_count} 个缓存条目")
```

## 工作原理

### 缓存键生成

```
格式: bi:cache:{dataset_id}:{hash(question)}
示例: bi:cache:1:9c8d0850fd8ef41bf0f52f211adfc4ea
```

- 相同数据集 + 相同问题 = 相同缓存键
- 问题使用 MD5 哈希，确保唯一性

### 缓存流程

```
用户提问
   ↓
检查缓存 (allow_cache=True)
   ↓
[命中] → 返回缓存结果 (from_cache=True)
   ↓
[未命中] → 执行 AI 生成 + SQL 查询
   ↓
查询成功 → 写入缓存 (TTL: 300s)
   ↓
返回结果 (from_cache=False)
```

### 自动清理时机

1. **数据集训练完成**：`train_dataset()` 完成后自动清除
2. **业务术语训练**：`train_term()` 完成后自动清除
3. **缓存过期**：超过 TTL 时间后 Redis 自动删除

## 异常处理

### Redis 连接失败

系统会自动降级，不影响核心功能：

```
2026-01-06 18:00:00 WARNING Redis connection failed: Connection refused. Cache disabled.
```

- ✅ 查询仍正常执行
- ✅ 只是不使用缓存
- ✅ 不抛出异常

### 缓存读写失败

单次缓存操作失败不影响查询：

```python
# 读缓存失败 → 继续执行查询
# 写缓存失败 → 返回查询结果（只是不缓存）
```

## 性能优化

### 缓存命中率监控

通过日志查看缓存命中情况：

```
INFO Cache hit for dataset 1, question: 查询销售数据...
DEBUG Cache miss for dataset 1
```

### 调整 TTL

根据业务特点调整缓存时间：

```bash
# 数据更新频繁 - 短 TTL
REDIS_CACHE_TTL=60

# 数据相对稳定 - 长 TTL
REDIS_CACHE_TTL=600
```

### Redis 内存优化

配置 Redis 最大内存和淘汰策略：

```bash
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru  # LRU 淘汰策略
```

## 测试

运行缓存功能测试：

```bash
cd backend
python3 test_redis_cache.py
```

测试覆盖：
- ✅ Redis 连接
- ✅ 缓存键生成
- ✅ 序列化/反序列化
- ✅ 缓存读写
- ✅ 缓存清除
- ✅ Redis 异常降级

## 最佳实践

### 1. 生产环境配置

```bash
# 使用独立 Redis 实例
REDIS_URL=redis://redis-server:6379/0

# 配置连接池（已内置）
# 配置超时时间（已设置 2 秒）
```

### 2. 监控建议

- 监控 Redis 内存使用
- 监控缓存命中率
- 设置 Redis 连接告警

### 3. 缓存策略

- 只缓存成功的查询结果
- 不缓存错误或澄清响应
- 定期清理过期数据（Redis 自动）

## 常见问题

### Q1: Redis 未启动会影响系统吗？

**A**: 不会。系统会自动检测并降级，所有功能正常工作，只是不使用缓存。

### Q2: 如何查看缓存是否生效？

**A**: 检查返回结果中的 `from_cache` 字段：
- `from_cache: true` - 来自缓存
- `from_cache: false` - 实时查询

### Q3: 什么情况下需要手动清除缓存？

**A**: 通常不需要手动清除。以下场景已自动处理：
- 数据集重新训练
- 添加业务术语
- 缓存过期（TTL）

只有在数据库数据发生变化时，可能需要手动清除。

### Q4: 缓存占用多少内存？

**A**: 取决于查询结果大小。一般：
- 简单查询（几行数据）: ~1-5 KB
- 复杂查询（百行数据）: ~10-50 KB
- 建议为每个数据集预留 10-100 MB

### Q5: 如何禁用缓存功能？

**A**: 有两种方式：
1. 不启动 Redis（自动降级）
2. 调用时传入 `allow_cache=False`

## 相关文件

- `backend/app/services/vanna_manager.py` - 缓存实现
- `backend/app/core/config.py` - 配置项
- `backend/test_redis_cache.py` - 测试脚本
- `requirements.txt` - Redis 依赖

## 更新日志

**2026-01-06**
- ✅ 实现 Redis 缓存功能
- ✅ 添加异常降级机制
- ✅ 集成自动清理功能
- ✅ 完成测试验证
