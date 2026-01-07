from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import datasource, dataset, chat, dashboard, auth, admin
from app.core.config import settings
from app.core.redis import redis_service
from app.db.session import engine
from app.models import metadata

# Create tables
metadata.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动和关闭事件"""
    # 启动事件
    print("🚀 启动 Universal BI 服务...")
    try:
        await redis_service.init()
    except Exception as e:
        print(f"⚠️ Redis 初始化失败，将在无缓存模式下运行: {e}")
    
    yield
    
    # 关闭事件
    print("🛑 关闭 Universal BI 服务...")
    await redis_service.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasource.router, prefix=f"{settings.API_V1_STR}/datasources", tags=["datasources"])
app.include_router(dataset.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["datasets"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboards", tags=["dashboards"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

@app.get("/")
def root():
    return {"message": "Welcome to Universal BI API"}
