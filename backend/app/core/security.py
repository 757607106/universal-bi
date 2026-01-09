from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
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

# 用于密钥派生的固定盐（生产环境应使用环境变量）
# 注意：更改此值会导致无法解密之前加密的数据
_ENCRYPTION_SALT = b"universal_bi_encryption_salt_v1"

# Redis 客户端（用于 Token 黑名单）
_redis_client = None
_redis_available = False

# 内存级别的黑名单备份（Redis 不可用时使用）
# 格式: {token_hash: expire_timestamp}
# 注意：内存黑名单在服务重启后会丢失
_memory_blacklist: dict = {}
_memory_blacklist_max_size = 10000  # 最大存储数量，防止内存泄漏

def _get_token_hash(token: str) -> str:
    """生成 Token 的哈希值用于存储（避免存储完整 Token）"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:32]

def _cleanup_memory_blacklist():
    """清理内存黑名单中过期的条目"""
    global _memory_blacklist
    now = datetime.utcnow().timestamp()
    _memory_blacklist = {k: v for k, v in _memory_blacklist.items() if v > now}

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

def get_cipher_suite(secret_key: str = None):
    """
    获取 Fernet 加密套件
    使用 PBKDF2 从 SECRET_KEY 派生 32 字节密钥，比简单 padding 更安全
    
    Args:
        secret_key: 可选的密钥，不提供则使用 settings.SECRET_KEY
    """
    # 使用 PBKDF2 密钥派生函数
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_ENCRYPTION_SALT,
        iterations=100_000,  # OWASP 推荐的迭代次数
    )
    key_to_use = secret_key if secret_key else settings.SECRET_KEY
    key = kdf.derive(key_to_use.encode())
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_password(password: str) -> str:
    cipher_suite = get_cipher_suite()
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码，支持密钥轮换
    
    先尝试使用当前 SECRET_KEY 解密，
    如果失败则依次尝试 OLD_SECRET_KEYS 列表中的旧密钥
    
    Args:
        encrypted_password: 加密后的密码
        
    Returns:
        str: 解密后的明文密码
        
    Raises:
        Exception: 所有密钥都无法解密时抛出异常
    """
    # 1. 尝试使用当前密钥解密
    try:
        cipher_suite = get_cipher_suite()
        return cipher_suite.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        logger.debug(f"Current key failed to decrypt: {e}")
    
    # 2. 尝试使用旧密钥列表解密
    for old_key in settings.old_secret_keys_list:
        try:
            cipher_suite = get_cipher_suite(old_key)
            decrypted = cipher_suite.decrypt(encrypted_password.encode()).decode()
            logger.warning(f"Decrypted using an old key. Consider re-encrypting with current key.")
            return decrypted
        except Exception:
            continue
    
    # 3. 所有密钥都失败
    raise Exception(
        "无法解密密码：当前密钥和所有旧密钥都失败。"
        "可能的原因：1) 密钥已更改且未配置 OLD_SECRET_KEYS；"
        "2) 数据已损坏。请使用「重新连接」功能重新设置密码。"
    )

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
    优先使用 Redis，Redis 不可用时使用内存备份

    Args:
        token: JWT Token 字符串

    Returns:
        bool: 是否成功添加到黑名单
    """
    global _memory_blacklist

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
        token_hash = _get_token_hash(token)

        # 尝试使用 Redis
        redis_client = get_redis_client()
        if redis_client:
            try:
                key = f"blacklist:token:{token_hash}"
                redis_client.setex(key, ttl, "revoked")
                logger.info(f"Token added to Redis blacklist, TTL: {ttl}s")
                return True
            except RedisError as e:
                logger.warning(f"Redis error, falling back to memory blacklist: {e}")

        # Redis 不可用或出错，使用内存备份
        # 定期清理过期条目
        if len(_memory_blacklist) > _memory_blacklist_max_size:
            _cleanup_memory_blacklist()

        # 如果清理后仍然超过限制，移除最早的条目
        if len(_memory_blacklist) >= _memory_blacklist_max_size:
            # 移除最早过期的 10% 条目
            sorted_items = sorted(_memory_blacklist.items(), key=lambda x: x[1])
            to_remove = len(_memory_blacklist) // 10
            for k, _ in sorted_items[:to_remove]:
                del _memory_blacklist[k]

        _memory_blacklist[token_hash] = exp
        logger.info(f"Token added to memory blacklist, TTL: {ttl}s")
        return True

    except JWTError as e:
        logger.error(f"Failed to decode token: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when adding token to blacklist: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    检查 Token 是否在黑名单中
    优先检查 Redis，Redis 不可用时检查内存备份

    Args:
        token: JWT Token 字符串

    Returns:
        bool: Token 是否在黑名单中（True=已撤销）
    """
    token_hash = _get_token_hash(token)

    # 尝试使用 Redis
    redis_client = get_redis_client()
    if redis_client:
        try:
            key = f"blacklist:token:{token_hash}"
            result = redis_client.exists(key)
            if result > 0:
                return True
        except RedisError as e:
            logger.warning(f"Redis error when checking blacklist, falling back to memory: {e}")

    # 检查内存黑名单
    if token_hash in _memory_blacklist:
        expire_time = _memory_blacklist[token_hash]
        now = datetime.utcnow().timestamp()
        if expire_time > now:
            return True
        else:
            # 已过期，清理
            del _memory_blacklist[token_hash]

    return False
