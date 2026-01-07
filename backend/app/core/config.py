
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """应用配置类 - 所有配置项统一从.env文件读取"""
    
    # ========== 应用基础配置 ==========
    PROJECT_NAME: str = "Universal BI"
    API_V1_STR: str = "/api/v1"
    
    # ========== JWT安全配置 ==========
    SECRET_KEY: str = "change_this_to_a_secure_random_key_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
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
    VN_PG_HOST: str = "localhost"
    VN_PG_PORT: int = 5432
    VN_PG_DB: str = "universal_bi_vector"
    VN_PG_USER: str = "postgres"
    VN_PG_PASSWORD: str = "postgres"
    
    # ========== ChromaDB配置 ==========
    # 用于Vanna向量存储和检索
    CHROMA_PERSIST_DIR: str = "./chroma_db"  # ChromaDB持久化目录
    CHROMA_N_RESULTS: int = 10  # 向量检索返回结果数量

    class Config:
        case_sensitive = True
        env_file = ".env"  # 统一从.env文件读取配置
        env_file_encoding = 'utf-8'

settings = Settings()

