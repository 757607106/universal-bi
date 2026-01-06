
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Universal BI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change_this_to_a_secure_random_key_in_production"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./sql_app.db"

    # Vanna & LLM Config
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"
    
    # Redis Config
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes default
    
    # Vector DB Config (PGVector)
    # Defaults to using the same DB as main app if not specified, but usually separate for Vanna
    VN_PG_HOST: str = "localhost"
    VN_PG_PORT: int = 5432
    VN_PG_DB: str = "universal_bi_vector"
    VN_PG_USER: str = "postgres"
    VN_PG_PASSWORD: str = "postgres"

    class Config:
        case_sensitive = True

settings = Settings()
