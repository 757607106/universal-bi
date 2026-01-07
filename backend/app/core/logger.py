"""
结构化日志系统配置
基于 structlog 实现，支持生产环境 JSON 格式和开发环境彩色输出
"""
import logging
import sys
from typing import Any
import structlog
from structlog.types import EventDict, Processor
from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加应用级上下文信息"""
    event_dict["app"] = settings.PROJECT_NAME
    return event_dict


def setup_logging() -> None:
    """
    初始化结构化日志系统
    - 生产环境(DEV=False): JSON 格式输出
    - 开发环境(DEV=True): 彩色易读格式输出
    - 拦截标准库 logging 并重定向到 structlog
    """
    # 共享的 processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # 合并上下文变量（如 request_id）
        structlog.stdlib.add_log_level,  # 添加日志级别
        structlog.stdlib.add_logger_name,  # 添加 logger 名称
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO 8601 时间戳
        add_app_context,  # 添加应用名称
        structlog.stdlib.PositionalArgumentsFormatter(),  # 处理位置参数
        structlog.processors.StackInfoRenderer(),  # 渲染堆栈信息
        structlog.processors.format_exc_info,  # 格式化异常信息
        structlog.processors.UnicodeDecoder(),  # 解码 Unicode
    ]

    # 根据环境选择渲染器
    if settings.DEV:
        # 开发环境：彩色控制台输出
        console_renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )
    else:
        # 生产环境：JSON 格式输出
        console_renderer = structlog.processors.JSONRenderer()

    # 配置 structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            console_renderer,
        ],
    )

    # 配置 handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if not settings.DEV else logging.DEBUG)

    # 拦截 uvicorn 和 fastapi 日志
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []  # 移除默认 handler
        logger.propagate = True  # 传播到根 logger


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    获取结构化 logger 实例
    
    Args:
        name: logger 名称，默认使用调用模块的名称
        
    Returns:
        structlog.stdlib.BoundLogger 实例
    """
    return structlog.get_logger(name)
