#!/usr/bin/env python3
"""
清除 Redis 缓存脚本
支持清除指定数据集或所有缓存
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.vanna_manager import VannaManager
from app.db.session import SessionLocal


def clear_dataset_cache(dataset_id: int):
    """清除指定数据集的缓存"""
    db = SessionLocal()
    try:
        cleared = VannaManager.clear_cache(dataset_id)
        if cleared >= 0:
            print(f"✓ 已清除数据集 {dataset_id} 的 {cleared} 个缓存条目")
        else:
            print(f"✗ Redis 不可用，无法清除缓存")
    finally:
        db.close()


def clear_all_cache():
    """清除所有数据集的缓存"""
    import redis
    from app.core.config import settings
    
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        pattern = "bi:cache:*"
        keys = client.keys(pattern)
        
        if keys:
            deleted = client.delete(*keys)
            print(f"✓ 已清除所有缓存，共删除 {deleted} 个条目")
        else:
            print("ℹ 没有找到任何缓存条目")
    except Exception as e:
        print(f"✗ 清除失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("Redis 缓存清除工具")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        # 命令行参数模式
        if sys.argv[1] == "all":
            print("清除所有缓存...")
            clear_all_cache()
        else:
            try:
                dataset_id = int(sys.argv[1])
                print(f"清除数据集 {dataset_id} 的缓存...")
                clear_dataset_cache(dataset_id)
            except ValueError:
                print("✗ 参数错误，请提供数据集 ID（数字）或 'all'")
                print()
                print("使用方法:")
                print("  python clear_cache.py <dataset_id>  # 清除指定数据集")
                print("  python clear_cache.py all           # 清除所有缓存")
    else:
        # 交互模式
        print("请选择操作:")
        print("  1. 清除指定数据集的缓存")
        print("  2. 清除所有缓存")
        print("  3. 退出")
        print()
        
        choice = input("请输入选项 (1/2/3): ").strip()
        
        if choice == "1":
            dataset_id_str = input("请输入数据集 ID: ").strip()
            try:
                dataset_id = int(dataset_id_str)
                clear_dataset_cache(dataset_id)
            except ValueError:
                print("✗ 无效的数据集 ID")
        elif choice == "2":
            confirm = input("确认清除所有缓存? (y/n): ").strip().lower()
            if confirm == 'y':
                clear_all_cache()
            else:
                print("已取消")
        elif choice == "3":
            print("退出")
        else:
            print("✗ 无效的选项")
    
    print()


if __name__ == "__main__":
    main()
