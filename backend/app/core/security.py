from cryptography.fernet import Fernet
import base64
from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import redis
from redis.exceptions import RedisError
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis 客户端（用于 Token 黑名单）
_redis_client = None
_redis_available = False

def get_redis_client():
    """
    获取 Redis 客户端（复用缓存连接）
    用于 Token 黑名单管理
    """
    global _redis_client, _redis_available
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            _redis_client.ping()
            _redis_available = True
            logger.info(f"Redis connected for token blacklist: {settings.REDIS_URL}")
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Token blacklist disabled.")
            _redis_client = None
            _redis_available = False
        except Exception as e:
            logger.warning(f"Unexpected error connecting to Redis: {e}. Token blacklist disabled.")
            _redis_client = None
            _redis_available = False
    
    return _redis_client if _redis_available else None

def get_cipher_suite():
    # Ensure the key is 32 url-safe base64-encoded bytes
    # For simplicity in this demo, we derive a key or use a fixed one if provided
    # In production, use a proper key management system
    key = settings.SECRET_KEY
    if len(key) < 32:
        key = key.ljust(32, '0')
    key = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(key)

def encrypt_password(password: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def add_token_to_blacklist(token: str) -> bool:
    """
    将 Token 添加到黑名单
    
    Args:
        token: JWT Token 字符串
    
    Returns:
        bool: 是否成功添加到黑名单
    """
    redis_client = get_redis_client()
    if not redis_client:
        logger.warning("Redis unavailable, token blacklist not applied")
        return False
    
    try:
        # 解析 Token 获取过期时间
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp")
        
        if not exp:
            logger.warning("Token has no expiration time")
            return False
        
        # 计算剩余有效期（秒）
        expire_time = datetime.fromtimestamp(exp)
        now = datetime.utcnow()
        
        if expire_time <= now:
            # Token 已过期，无需加入黑名单
            logger.info("Token already expired, skipping blacklist")
            return True
        
        ttl = int((expire_time - now).total_seconds())
        
        # 将 Token 存入 Redis，设置过期时间为剩余有效期
        key = f"blacklist:token:{token}"
        redis_client.setex(key, ttl, "revoked")
        
        logger.info(f"Token added to blacklist, TTL: {ttl}s")
        return True
        
    except JWTError as e:
        logger.error(f"Failed to decode token: {e}")
        return False
    except RedisError as e:
        logger.error(f"Redis error when adding token to blacklist: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when adding token to blacklist: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    检查 Token 是否在黑名单中
    
    Args:
        token: JWT Token 字符串
    
    Returns:
        bool: Token 是否在黑名单中（True=已撤销）
    """
    redis_client = get_redis_client()
    if not redis_client:
        # Redis 不可用时，默认不检查黑名单（降级策略）
        return False
    
    try:
        key = f"blacklist:token:{token}"
        result = redis_client.exists(key)
        return result > 0
    except RedisError as e:
        logger.error(f"Redis error when checking token blacklist: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when checking token blacklist: {e}")
        return False
