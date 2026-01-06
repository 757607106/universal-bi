from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import settings

# 判断数据库类型并设置相应的连接参数
if settings.SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
    # SQLite 配置
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        connect_args={"check_same_thread": False}
    )
else:
    # MySQL/PostgreSQL 配置 - 使用连接池
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        poolclass=QueuePool,
        pool_size=10,  # 连接池大小
        max_overflow=20,  # 最大溢出连接数
        pool_timeout=30,  # 获取连接超时时间(秒)
        pool_recycle=3600,  # 连接回收时间(秒)，防止连接超时
        pool_pre_ping=True,  # 连接前检查可用性
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
