"""
测试 Redis 服务基础功能
"""
import asyncio
from app.core.redis import redis_service, generate_cache_key


async def test_redis_service():
    """测试 Redis 服务基础功能"""
    print("=" * 60)
    print("测试 Redis 服务基础功能")
    print("=" * 60)
    
    try:
        # 1. 初始化 Redis 连接
        print("\n[1] 初始化 Redis 连接...")
        await redis_service.init()
        print("✅ Redis 连接成功")
        
        # 2. 测试 generate_cache_key
        print("\n[2] 测试缓存键生成...")
        key1 = generate_cache_key("bi:sql_cache", 1, "查询用户表")
        key2 = generate_cache_key("bi:sql_cache", 1, "查询用户表")
        key3 = generate_cache_key("bi:sql_cache", 2, "查询用户表")
        
        print(f"Key 1: {key1}")
        print(f"Key 2: {key2}")
        print(f"Key 3: {key3}")
        
        assert key1 == key2, "相同参数应该生成相同的 key"
        assert key1 != key3, "不同参数应该生成不同的 key"
        print("✅ 缓存键生成正常")
        
        # 3. 测试基本的 set/get
        print("\n[3] 测试基本的 set/get...")
        test_key = "test:string"
        test_value = "Hello Redis!"
        
        await redis_service.set(test_key, test_value, expire=10)
        result = await redis_service.get(test_key)
        
        print(f"写入: {test_value}")
        print(f"读取: {result}")
        assert result == test_value, "读取的值应该等于写入的值"
        print("✅ 基本 set/get 正常")
        
        # 4. 测试 JSON 序列化
        print("\n[4] 测试 JSON 序列化...")
        test_dict_key = "test:dict"
        test_dict = {"sql": "SELECT * FROM users", "dataset_id": 1, "count": 100}
        
        await redis_service.set(test_dict_key, test_dict, expire=10)
        result_dict = await redis_service.get(test_dict_key)
        
        print(f"写入: {test_dict}")
        print(f"读取: {result_dict}")
        assert result_dict == test_dict, "读取的字典应该等于写入的字典"
        print("✅ JSON 序列化正常")
        
        # 5. 测试 exists
        print("\n[5] 测试 exists...")
        exists1 = await redis_service.exists(test_key)
        exists2 = await redis_service.exists("not:exist:key")
        
        print(f"存在的键: {exists1}")
        print(f"不存在的键: {exists2}")
        assert exists1 is True, "存在的键应该返回 True"
        assert exists2 is False, "不存在的键应该返回 False"
        print("✅ exists 正常")
        
        # 6. 测试 delete
        print("\n[6] 测试 delete...")
        await redis_service.delete(test_key)
        result_after_delete = await redis_service.get(test_key)
        
        print(f"删除后读取: {result_after_delete}")
        assert result_after_delete is None, "删除后应该读取不到值"
        print("✅ delete 正常")
        
        # 7. 测试 SQL 缓存场景
        print("\n[7] 测试 SQL 缓存场景...")
        dataset_id = 1
        question = "查询最近7天的销售数据"
        cached_sql = "SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        
        cache_key = generate_cache_key("bi:sql_cache", dataset_id, question)
        print(f"Cache Key: {cache_key}")
        
        # 写入缓存 (24小时 = 86400秒)
        await redis_service.set(cache_key, cached_sql, expire=86400)
        print(f"✅ SQL 已缓存: {cached_sql[:50]}...")
        
        # 读取缓存
        cached_result = await redis_service.get(cache_key)
        print(f"✅ SQL 缓存命中: {cached_result[:50]}...")
        assert cached_result == cached_sql, "缓存的 SQL 应该等于原始 SQL"
        
        # 清理测试数据
        await redis_service.delete(cache_key)
        await redis_service.delete(test_dict_key)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭连接
        print("\n[关闭] 关闭 Redis 连接...")
        await redis_service.close()
        print("✅ Redis 连接已关闭")


if __name__ == "__main__":
    asyncio.run(test_redis_service())
