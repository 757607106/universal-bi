"""
Vanna 缓存服务

纯异步的 Redis 缓存服务，用于 SQL 查询缓存。
消除了 nest_asyncio 的使用。
"""

from app.core.redis import redis_service, generate_cache_key
from app.core.logger import get_logger

logger = get_logger(__name__)


class VannaCacheService:
    """
    纯异步缓存服务

    提供 SQL 缓存的异步读写操作，消除 nest_asyncio hack。
    """

    # 默认缓存 TTL（24小时）
    DEFAULT_TTL = 86400

    @classmethod
    async def clear_cache(cls, dataset_id: int) -> int:
        """
        清除指定数据集的所有缓存查询

        Args:
            dataset_id: 数据集ID

        Returns:
            int: 删除的键数量, -1 表示 Redis 不可用
        """
        try:
            total_deleted = 0

            if redis_service.redis_client:
                # 1. 清除结果缓存
                result_pattern = f"bi:cache:{dataset_id}:*"
                async for key in redis_service.redis_client.scan_iter(match=result_pattern):
                    await redis_service.delete(key)
                    total_deleted += 1

                # 2. 清除 SQL 缓存
                sql_pattern = f"bi:sql_cache:{dataset_id}:*"
                async for key in redis_service.redis_client.scan_iter(match=sql_pattern):
                    await redis_service.delete(key)
                    total_deleted += 1

                logger.info(f"Cleared {total_deleted} cache entries for dataset {dataset_id}")
            else:
                logger.warning("Redis unavailable, cannot clear cache")
                return -1

            return total_deleted
        except Exception as e:
            logger.error(f"Failed to clear cache for dataset {dataset_id}: {e}")
            return -1

    @classmethod
    async def get_cached_sql(cls, dataset_id: int, question: str) -> str | None:
        """
        获取缓存的 SQL

        Args:
            dataset_id: 数据集ID
            question: 用户问题

        Returns:
            str | None: 缓存的 SQL，不存在则返回 None
        """
        try:
            cache_key = generate_cache_key("bi:sql_cache", dataset_id, question)
            cached_sql = await redis_service.get(cache_key)
            if cached_sql:
                logger.debug(f"SQL cache hit for dataset {dataset_id}")
            return cached_sql
        except Exception as e:
            logger.warning(f"Failed to get cached SQL: {e}")
            return None

    @classmethod
    async def cache_sql(cls, dataset_id: int, question: str, sql: str, ttl: int = None) -> bool:
        """
        缓存 SQL 查询结果

        Args:
            dataset_id: 数据集ID
            question: 用户问题
            sql: 生成的 SQL
            ttl: 缓存过期时间（秒），默认 24 小时

        Returns:
            bool: 是否成功缓存
        """
        try:
            cache_key = generate_cache_key("bi:sql_cache", dataset_id, question)
            ttl = ttl or cls.DEFAULT_TTL
            await redis_service.set(cache_key, sql, ttl=ttl)
            logger.debug(f"Cached SQL for dataset {dataset_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cache SQL: {e}")
            return False

    @classmethod
    async def delete_cached_sql(cls, dataset_id: int, question: str) -> bool:
        """
        删除指定的 SQL 缓存

        Args:
            dataset_id: 数据集ID
            question: 用户问题

        Returns:
            bool: 是否成功删除
        """
        try:
            cache_key = generate_cache_key("bi:sql_cache", dataset_id, question)
            await redis_service.delete(cache_key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete cached SQL: {e}")
            return False
