"""
Redis 缓存功能快速示例
演示如何使用和测试缓存功能
"""
import asyncio
from app.services.vanna_manager import VannaManager
from app.db.session import SessionLocal


async def demo_cache_usage():
    """演示缓存使用"""
    db = SessionLocal()
    
    try:
        dataset_id = 1  # 假设数据集 ID 为 1
        question = "查询总销售额"
        
        print("=" * 60)
        print("示例 1: 第一次查询（Cache Miss）")
        print("=" * 60)
        
        # 第一次查询
        result1 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=True  # 启用缓存（默认）
        )
        
        print(f"SQL: {result1.get('sql')}")
        print(f"from_cache: {result1.get('from_cache', False)}")
        print(f"执行步骤: {result1.get('steps', [])[-1]}")
        print()
        
        print("=" * 60)
        print("示例 2: 第二次相同查询（Cache Hit）")
        print("=" * 60)
        
        # 第二次查询 - 应该从缓存返回
        result2 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=True
        )
        
        print(f"SQL: {result2.get('sql')}")
        print(f"from_cache: {result2.get('from_cache', False)}")
        print(f"执行步骤: {result2.get('steps', [])[-1]}")
        print()
        
        print("=" * 60)
        print("示例 3: 强制跳过缓存")
        print("=" * 60)
        
        # 跳过缓存
        result3 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=False  # 禁用缓存
        )
        
        print(f"SQL: {result3.get('sql')}")
        print(f"from_cache: {result3.get('from_cache', False)}")
        print(f"执行步骤: {result3.get('steps', [])[-1]}")
        print()
        
        print("=" * 60)
        print("示例 4: 清除缓存")
        print("=" * 60)
        
        # 清除缓存
        cleared = VannaManager.clear_cache(dataset_id)
        print(f"清除了 {cleared} 个缓存条目")
        print()
        
        print("=" * 60)
        print("示例 5: 清除缓存后再次查询（Cache Miss）")
        print("=" * 60)
        
        # 清除后再次查询
        result4 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=True
        )
        
        print(f"SQL: {result4.get('sql')}")
        print(f"from_cache: {result4.get('from_cache', False)}")
        print(f"执行步骤: {result4.get('steps', [])[-1]}")
        print()
        
    finally:
        db.close()


async def demo_performance_comparison():
    """演示性能对比"""
    import time
    
    db = SessionLocal()
    
    try:
        dataset_id = 1
        question = "查询用户统计数据"
        
        print("=" * 60)
        print("性能对比测试")
        print("=" * 60)
        
        # 清除缓存
        VannaManager.clear_cache(dataset_id)
        
        # 不使用缓存
        start = time.time()
        result1 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=False
        )
        no_cache_time = time.time() - start
        
        # 使用缓存（第一次）
        start = time.time()
        result2 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=True
        )
        first_cache_time = time.time() - start
        
        # 使用缓存（第二次，命中缓存）
        start = time.time()
        result3 = await VannaManager.generate_result(
            dataset_id=dataset_id,
            question=question,
            db_session=db,
            allow_cache=True
        )
        cached_time = time.time() - start
        
        print(f"不使用缓存: {no_cache_time:.3f} 秒")
        print(f"缓存未命中: {first_cache_time:.3f} 秒")
        print(f"缓存命中:   {cached_time:.3f} 秒")
        print(f"性能提升:   {(no_cache_time / cached_time):.1f}x")
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Redis 缓存功能示例")
    print("=" * 60)
    print()
    
    # 运行示例
    # asyncio.run(demo_cache_usage())
    
    # 性能对比（需要真实数据集）
    # asyncio.run(demo_performance_comparison())
    
    print("提示：")
    print("- 请确保 Redis 已启动")
    print("- 请确保数据集已训练")
    print("- 取消注释 asyncio.run() 行来运行示例")
    print()
