import time
import uuid
import warnings
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from asgi_correlation_id import CorrelationIdMiddleware
import structlog
from app.api.v1.endpoints import datasource, dataset, chat, dashboard, auth, admin, upload, data_table
from app.core.config import settings
from app.core.logger import setup_logging, get_logger
from app.core.redis import redis_service
from app.db.session import engine
from app.models import metadata

# === 安全检查 ===
DEFAULT_SECRET_KEY = "change_this_to_a_secure_random_key_in_production"

def _check_security_config():
    """检查安全配置，在开发环境警告，生产环境拒绝启动"""
    issues = []

    # 检查 JWT Secret Key
    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        msg = "JWT SECRET_KEY is using default value! This is a security risk."
        if not settings.DEV:
            raise RuntimeError(f"SECURITY ERROR: {msg} Please set a strong random SECRET_KEY in .env file.")
        issues.append(msg)

    if len(settings.SECRET_KEY) < 32:
        msg = f"JWT SECRET_KEY is too short ({len(settings.SECRET_KEY)} chars). Recommended minimum is 32 characters."
        if not settings.DEV:
            raise RuntimeError(f"SECURITY ERROR: {msg}")
        issues.append(msg)

    # 在开发环境打印警告
    if issues:
        for issue in issues:
            warnings.warn(f"SECURITY WARNING: {issue}", UserWarning, stacklevel=2)

# 执行安全检查
_check_security_config()

# Create tables
metadata.Base.metadata.create_all(bind=engine)

# 初始化结构化日志系统
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动和关闭事件"""
    # 启动事件
    logger.info("Starting Universal BI service", env="dev" if settings.DEV else "prod")
    try:
        await redis_service.init()
        logger.info("Redis initialized successfully")
    except Exception as e:
        logger.warning("Redis initialization failed, running without cache", error=str(e))
    
    yield
    
    # 关闭事件
    logger.info("Shutting down Universal BI service")
    await redis_service.close()
    logger.info("Service stopped")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False  # 禁用自动斜杠重定向，避免307重定向导致Authorization头丢失
)

# 添加请求 ID 中间件（自动生成并注入上下文）
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4()),
    transformer=lambda x: x,
)

# 添加日志中间件（记录请求和响应）
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    记录每个 HTTP 请求的详细信息
    - 请求开始: method, path, client_ip, request_id
    - 请求结束: status_code, process_time_ms
    """
    # 获取请求 ID（由 CorrelationIdMiddleware 生成）
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # 将 request_id 绑定到上下文（后续所有日志自动带上）
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    # 记录请求开始
    start_time = time.time()
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        query_params=str(request.query_params) if request.query_params else None,
    )
    
    # 处理请求
    try:
        response = await call_next(request)
        process_time_ms = (time.time() - start_time) * 1000
        
        # 记录请求结束
        logger.info(
            "Request completed",
            status_code=response.status_code,
            process_time_ms=round(process_time_ms, 2),
        )
        
        # 将 request_id 添加到响应头
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        process_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "Request failed",
            error=str(e),
            error_type=type(e).__name__,
            process_time_ms=round(process_time_ms, 2),
            exc_info=True,
        )
        raise

# Set CORS origins from configuration
# 在生产环境中，如果配置了 "*" 则发出警告
cors_origins = settings.cors_origins_list
if not settings.DEV and "*" in cors_origins:
    warnings.warn(
        "SECURITY WARNING: CORS_ORIGINS is set to '*' in production mode. "
        "This allows any website to make requests to your API. "
        "Please configure specific origins in .env: CORS_ORIGINS=https://yourdomain.com",
        UserWarning, stacklevel=1
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(upload.router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])
app.include_router(data_table.router, prefix=f"{settings.API_V1_STR}/data-tables", tags=["data-tables"])

@app.get("/")
def root():
    return {"message": "Welcome to Universal BI API"}
