
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """应用配置类 - 所有配置项统一从.env文件读取"""

    # ========== 应用基础配置 ==========
    PROJECT_NAME: str = "Universal BI"
    API_V1_STR: str = "/api/v1"
    DEV: bool = True  # 开发环境标志，True=开发环境（彩色日志），False=生产环境（JSON日志）

    # ========== JWT安全配置 ==========
    # ⚠️ 警告：SECRET_KEY 用于加密JWT Token和数据源密码
    # 生产环境必须修改为强随机字符串（至少32字符）
    # 如果密钥丢失或变更，所有已加密的数据源密码将无法解密
    # 推荐生成方式: openssl rand -hex 32
    SECRET_KEY: str = "change_this_to_a_secure_random_key_in_production"
    
    # 可选：旧密钥列表，用于密钥轮换时解密旧数据
    # 格式: "old_key_1,old_key_2,old_key_3" (逗号分隔)
    # 系统会先尝试用 SECRET_KEY 解密，失败后依次尝试 OLD_SECRET_KEYS
    OLD_SECRET_KEYS: str = ""
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @property
    def old_secret_keys_list(self) -> list[str]:
        """解析旧密钥列表"""
        if not self.OLD_SECRET_KEYS:
            return []
        return [key.strip() for key in self.OLD_SECRET_KEYS.split(",") if key.strip()]

    # ========== CORS配置 ==========
    # 允许的跨域来源，多个用逗号分隔，"*" 表示允许所有（仅开发环境）
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> list:
        """解析 CORS_ORIGINS 为列表"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # ========== 主数据库配置 ==========
    # 支持MySQL/PostgreSQL/SQLite，默认使用MySQL
    SQLALCHEMY_DATABASE_URI: str = "mysql+pymysql://root@localhost:3306/universal_bi?charset=utf8mb4"
    
    # ========== AI大模型配置 ==========
    # 阿里云通义千问API配置
    DASHSCOPE_API_KEY: str = ""  # 从.env或系统环境变量读取
    QWEN_MODEL: str = "qwen-max"  # 可选: qwen-max, qwen-plus, qwen-turbo
    
    # ========== Redis缓存配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 结果缓存过期时间（秒）- 5分钟
    SQL_CACHE_TTL: int = 604800  # SQL缓存过期时间（秒）- 7天
    
    # ========== 向量数据库配置 (PGVector) ==========
    # 用于Vanna训练数据存储
    VECTOR_STORE_TYPE: str = "chromadb"  # 可选: "pgvector", "chromadb"
    VN_PG_HOST: str = "localhost"
    VN_PG_PORT: int = 5432
    VN_PG_DB: str = "universal_bi_vector"
    VN_PG_USER: str = "postgres"
    VN_PG_PASSWORD: str = "postgres"

    @property
    def VN_PG_CONNECTION_STRING(self) -> str:
        """生成 PGVector 连接字符串"""
        return f"postgresql://{self.VN_PG_USER}:{self.VN_PG_PASSWORD}@{self.VN_PG_HOST}:{self.VN_PG_PORT}/{self.VN_PG_DB}"
    
    # ========== ChromaDB配置 ==========
    # 用于Vanna向量存储和检索
    CHROMA_PERSIST_DIR: str = "./chroma_db"  # ChromaDB持久化目录
    CHROMA_N_RESULTS: int = 10  # 向量检索返回结果数量

    # ========== Vanna API模式配置 ==========
    # 控制使用 Legacy API 还是 Agent API
    VANNA_API_MODE: str = "legacy"  # 可选: "legacy", "agent"

    # ========== DuckDB 配置 ==========
    # 用于多表分析的 DuckDB 数据库存储目录
    DUCKDB_DATABASE_DIR: str = "./duckdb_storage"  # DuckDB 数据库文件存储目录

    class Config:
        case_sensitive = True
        env_file = ".env"  # 统一从.env文件读取配置
        env_file_encoding = 'utf-8'

settings = Settings()

