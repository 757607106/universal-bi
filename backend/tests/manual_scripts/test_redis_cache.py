#!/usr/bin/env python3
"""
测试 Redis 缓存功能
验证缓存读写、异常降级、TTL 等特性
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.vanna_manager import VannaManager
from app.core.config import settings
import asyncio
import time


def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("测试 1: Redis 连接")
    print("=" * 60)
    
    redis_client = VannaManager._get_redis_client()
    
    if redis_client:
        print(f"✓ Redis 连接成功: {settings.REDIS_URL}")
        print(f"✓ Redis 可用状态: {VannaManager._redis_available}")
        
        # Test ping
        try:
            redis_client.ping()
            print("✓ Redis Ping 成功")
        except Exception as e:
            print(f"✗ Redis Ping 失败: {e}")
    else:
        print("✗ Redis 连接失败，缓存功能将被禁用")
    
    print()


def test_cache_key_generation():
    """测试缓存键生成"""
    print("=" * 60)
    print("测试 2: 缓存键生成")
    print("=" * 60)
    
    dataset_id = 1
    question1 = "查询销售数据"
    question2 = "查询销售数据"  # 相同问题
    question3 = "查询用户数据"  # 不同问题
    
    # 结果缓存键
    key1 = VannaManager._generate_cache_key(dataset_id, question1)
    key2 = VannaManager._generate_cache_key(dataset_id, question2)
    key3 = VannaManager._generate_cache_key(dataset_id, question3)
    
    print(f"[结果缓存键]")
    print(f"问题 1: {question1}")
    print(f"  缓存键: {key1}")
    print(f"问题 2: {question2}")
    print(f"  缓存键: {key2}")
    print(f"问题 3: {question3}")
    print(f"  缓存键: {key3}")
    
    if key1 == key2:
        print("✓ 相同问题生成相同结果缓存键")
    else:
        print("✗ 相同问题生成了不同结果缓存键")
    
    if key1 != key3:
        print("✓ 不同问题生成不同结果缓存键")
    else:
        print("✗ 不同问题生成了相同结果缓存键")
    
    # SQL 缓存键
    sql_key1 = VannaManager._generate_sql_cache_key(dataset_id, question1)
    sql_key2 = VannaManager._generate_sql_cache_key(dataset_id, question2)
    sql_key3 = VannaManager._generate_sql_cache_key(dataset_id, question3)
    
    print(f"\n[SQL 缓存键]")
    print(f"问题 1: {question1}")
    print(f"  SQL缓存键: {sql_key1}")
    print(f"问题 2: {question2}")
    print(f"  SQL缓存键: {sql_key2}")
    print(f"问题 3: {question3}")
    print(f"  SQL缓存键: {sql_key3}")
    
    if sql_key1 == sql_key2:
        print("✓ 相同问题生成相同 SQL 缓存键")
    else:
        print("✗ 相同问题生成了不同 SQL 缓存键")
    
    if sql_key1 != sql_key3:
        print("✓ 不同问题生成不同 SQL 缓存键")
    else:
        print("✗ 不同问题生成了相同 SQL 缓存键")
    
    if "sql_cache" in sql_key1 and "sql_cache" not in key1:
        print("✓ SQL 缓存键和结果缓存键使用不同前缀")
    else:
        print("✗ SQL 缓存键和结果缓存键前缀有问题")
    
    print()


def test_cache_serialization():
    """测试缓存序列化和反序列化"""
    print("=" * 60)
    print("测试 3: 缓存序列化")
    print("=" * 60)
    
    # Mock result data
    test_result = {
        "sql": "SELECT * FROM users LIMIT 10",
        "columns": ["id", "name", "email"],
        "rows": [
            {"id": 1, "name": "张三", "email": "zhang@example.com"},
            {"id": 2, "name": "李四", "email": "li@example.com"}
        ],
        "chart_type": "table",
        "steps": ["初始化完成", "SQL执行成功"],
        "from_cache": False
    }
    
    try:
        # Serialize
        serialized = VannaManager._serialize_cache_data(test_result)
        print(f"✓ 序列化成功，长度: {len(serialized)} 字节")
        print(f"  序列化数据预览: {serialized[:100]}...")
        
        # Deserialize
        deserialized = VannaManager._deserialize_cache_data(serialized)
        print(f"✓ 反序列化成功")
        
        # Verify
        if deserialized == test_result:
            print("✓ 数据一致性验证通过")
        else:
            print("✗ 数据一致性验证失败")
            print(f"  原始: {test_result}")
            print(f"  恢复: {deserialized}")
    
    except Exception as e:
        print(f"✗ 序列化测试失败: {e}")
    
    print()


def test_cache_read_write():
    """测试缓存读写"""
    print("=" * 60)
    print("测试 4: 缓存读写")
    print("=" * 60)
    
    redis_client = VannaManager._get_redis_client()
    
    if not redis_client:
        print("⚠ Redis 不可用，跳过读写测试")
        print()
        return
    
    dataset_id = 999  # 测试用数据集
    question = "测试查询问题"
    cache_key = VannaManager._generate_cache_key(dataset_id, question)
    
    # Mock result
    test_result = {
        "sql": "SELECT COUNT(*) FROM test_table",
        "columns": ["count"],
        "rows": [{"count": 100}],
        "chart_type": "table",
        "steps": ["测试步骤"],
        "from_cache": False
    }
    
    try:
        # Write to cache
        cache_data = VannaManager._serialize_cache_data(test_result)
        redis_client.setex(cache_key, 60, cache_data)  # 60s TTL
        print(f"✓ 缓存写入成功")
        print(f"  缓存键: {cache_key}")
        print(f"  TTL: 60 秒")
        
        # Read from cache
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print(f"✓ 缓存读取成功")
            
            result = VannaManager._deserialize_cache_data(cached_data)
            if result == test_result:
                print("✓ 缓存数据验证通过")
            else:
                print("✗ 缓存数据不一致")
        else:
            print("✗ 缓存读取失败，未找到数据")
        
        # Check TTL
        ttl = redis_client.ttl(cache_key)
        print(f"✓ 剩余 TTL: {ttl} 秒")
        
        # Cleanup
        redis_client.delete(cache_key)
        print(f"✓ 测试缓存已清理")
    
    except Exception as e:
        print(f"✗ 缓存读写测试失败: {e}")
    
    print()


def test_clear_cache():
    """测试清除缓存"""
    print("=" * 60)
    print("测试 5: 清除缓存")
    print("=" * 60)
    
    redis_client = VannaManager._get_redis_client()
    
    if not redis_client:
        print("⚠ Redis 不可用，跳过清除测试")
        print()
        return
    
    dataset_id = 888
    
    try:
        # Create multiple result cache entries
        for i in range(3):
            question = f"测试问题 {i}"
            cache_key = VannaManager._generate_cache_key(dataset_id, question)
            test_data = {"test": f"data_{i}"}
            redis_client.setex(
                cache_key,
                60,
                VannaManager._serialize_cache_data(test_data)
            )
        
        print(f"✓ 创建了 3 个结果缓存条目")
        
        # Create multiple SQL cache entries
        for i in range(3):
            question = f"测试SQL问题 {i}"
            sql_cache_key = VannaManager._generate_sql_cache_key(dataset_id, question)
            test_sql = f"SELECT * FROM table_{i}"
            redis_client.setex(sql_cache_key, 60, test_sql)
        
        print(f"✓ 创建了 3 个 SQL 缓存条目")
        
        # Check count
        result_pattern = f"bi:cache:{dataset_id}:*"
        sql_pattern = f"bi:sql_cache:{dataset_id}:*"
        result_keys_before = redis_client.keys(result_pattern)
        sql_keys_before = redis_client.keys(sql_pattern)
        print(f"✓ 清除前结果缓存数量: {len(result_keys_before)}")
        print(f"✓ 清除前 SQL 缓存数量: {len(sql_keys_before)}")
        
        # Clear cache
        cleared = VannaManager.clear_cache(dataset_id)
        print(f"✓ 清除缓存完成，删除了 {cleared} 个条目")
        
        # Verify
        result_keys_after = redis_client.keys(result_pattern)
        sql_keys_after = redis_client.keys(sql_pattern)
        
        if len(result_keys_after) == 0 and len(sql_keys_after) == 0:
            print("✓ 所有缓存清除验证通过")
        else:
            print(f"✗ 仍有 {len(result_keys_after)} 个结果缓存和 {len(sql_keys_after)} 个 SQL 缓存未清除")
    
    except Exception as e:
        print(f"✗ 清除缓存测试失败: {e}")
    
    print()


def test_redis_unavailable():
    """测试 Redis 不可用时的降级行为"""
    print("=" * 60)
    print("测试 6: Redis 异常降级")
    print("=" * 60)
    
    # Save original config
    original_url = settings.REDIS_URL
    
    try:
        # Set invalid Redis URL
        settings.REDIS_URL = "redis://invalid-host:9999/0"
        
        # Reset client to force reconnection
        VannaManager._redis_client = None
        VannaManager._redis_available = False
        
        print(f"✓ 设置无效 Redis URL: {settings.REDIS_URL}")
        
        # Try to get client
        redis_client = VannaManager._get_redis_client()
        
        if redis_client is None:
            print("✓ Redis 连接失败，客户端返回 None（符合预期）")
        else:
            print("✗ Redis 连接应该失败但返回了客户端")
        
        if not VannaManager._redis_available:
            print("✓ Redis 可用状态正确设置为 False")
        else:
            print("✗ Redis 可用状态应为 False")
        
        # Try clear_cache with unavailable Redis
        cleared = VannaManager.clear_cache(999)
        if cleared == -1:
            print("✓ clear_cache 正确处理了 Redis 不可用的情况（返回 -1）")
        else:
            print(f"✗ clear_cache 应该返回 -1，但返回了 {cleared}")
        
        print("✓ Redis 异常降级测试通过")
    
    except Exception as e:
        print(f"✗ Redis 异常降级测试失败: {e}")
    
    finally:
        # Restore original config
        settings.REDIS_URL = original_url
        VannaManager._redis_client = None
        VannaManager._redis_available = False
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Redis 缓存功能测试")
    print("=" * 60)
    print(f"Redis URL: {settings.REDIS_URL}")
    print(f"Result Cache TTL: {settings.REDIS_CACHE_TTL} 秒 (5 分钟)")
    print(f"SQL Cache TTL: {settings.SQL_CACHE_TTL} 秒 (7 天)")
    print()
    
    # Run tests
    test_redis_connection()
    test_cache_key_generation()
    test_cache_serialization()
    test_cache_read_write()
    test_clear_cache()
    test_redis_unavailable()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n提示：")
    print("- 如果 Redis 未运行，缓存功能将自动降级（不影响正常功能）")
    print("- 可以使用 'docker run -d -p 6379:6379 redis' 启动 Redis")
    print("- 或在 .env 文件中配置 REDIS_URL 指向现有 Redis 实例")
    print("\n缓存策略：")
    print("- 结果缓存: 缓存完整查询结果, TTL 5 分钟, 适合极短期重复查询")
    print("- SQL 缓存: 缓存 SQL 语句并重新执行, TTL 7 天, 省 Token 保数据时效")
    print()


if __name__ == "__main__":
    main()
