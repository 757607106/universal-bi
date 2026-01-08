"""
Redis 缓存服务基础层
提供异步 Redis 连接池和基础缓存操作
"""
import json
import pickle
import hashlib
from typing import Any, Optional
from redis import asyncio as aioredis
from app.core.config import settings


class RedisService:
    """Redis 异步服务类"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self._pool: Optional[aioredis.ConnectionPool] = None
    
    async def init(self):
        """初始化 Redis 连接池"""
        try:
            self._pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # 关闭自动解码，支持 pickle
                max_connections=10
            )
            self.redis_client = aioredis.Redis(connection_pool=self._pool)
            # 测试连接
            await self.redis_client.ping()
            print(f"✅ Redis 连接成功: {settings.REDIS_URL}")
        except Exception as e:
            print(f"❌ Redis 连接失败: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在返回 None
        """
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return None
            
            # 尝试 JSON 反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # 如果 JSON 失败，尝试 pickle
                try:
                    return pickle.loads(value)
                except Exception:
                    # 如果都失败，返回原始字节
                    return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            print(f"❌ Redis GET 失败 [{key}]: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        设置缓存值（支持自动序列化）
        
        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒），None 表示永不过期
            
        Returns:
            是否设置成功
        """
        if not self.redis_client:
            return False
        
        try:
            # 序列化策略：
            # 1. 基本类型（str/int/float/bool）→ JSON
            # 2. 字典/列表 → JSON
            # 3. 其他对象 → Pickle
            if isinstance(value, (str, int, float, bool, dict, list, type(None))):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = pickle.dumps(value)
            
            if expire:
                await self.redis_client.setex(key, expire, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            
            return True
        except Exception as e:
            print(f"❌ Redis SET 失败 [{key}]: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存键
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Redis DELETE 失败 [{key}]: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"❌ Redis EXISTS 失败 [{key}]: {e}")
            return False
    
    async def close(self):
        """关闭 Redis 连接池"""
        if self.redis_client:
            await self.redis_client.close()
        if self._pool:
            await self._pool.disconnect()
        print("✅ Redis 连接已关闭")


def generate_cache_key(prefix: str, *args) -> str:
    """
    生成唯一的缓存键（MD5 哈希）
    
    Args:
        prefix: 缓存键前缀（用于分类）
        *args: 任意数量的参数
        
    Returns:
        格式化的缓存键: {prefix}:{md5_hash}
        
    Example:
        >>> generate_cache_key("sql", 1, "SELECT * FROM users")
        'sql:a1b2c3d4e5f6...'
    """
    # 将所有参数转换为字符串并拼接
    parts = [str(arg) for arg in args]
    raw_key = ":".join(parts)
    
    # MD5 哈希
    hash_obj = hashlib.md5(raw_key.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    
    return f"{prefix}:{hash_hex}"


# 全局 Redis 服务实例
redis_service = RedisService()
