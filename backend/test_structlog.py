"""
测试 structlog 日志系统
验证日志输出格式和上下文绑定
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.logger import setup_logging, get_logger
from app.core.config import settings

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)

def test_basic_logging():
    """测试基础日志输出"""
    print("\n" + "="*60)
    print("测试 1: 基础日志输出")
    print("="*60 + "\n")
    
    logger.debug("这是一条 DEBUG 日志", detail="调试信息")
    logger.info("这是一条 INFO 日志", user_id=123, action="login")
    logger.warning("这是一条 WARNING 日志", warning_code="W001")
    logger.error("这是一条 ERROR 日志", error_code="E500", trace_id="abc123")


def test_context_binding():
    """测试上下文绑定"""
    print("\n" + "="*60)
    print("测试 2: 上下文绑定 (request_id)")
    print("="*60 + "\n")
    
    import structlog
    
    # 模拟请求 1
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-001")
    logger.info("处理请求 1", endpoint="/api/users")
    logger.info("查询数据库", table="users", query_time_ms=25.3)
    logger.info("请求完成", status_code=200)
    
    # 模拟请求 2
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-002")
    logger.info("处理请求 2", endpoint="/api/orders")
    logger.warning("数据库慢查询", table="orders", query_time_ms=350.7)
    logger.info("请求完成", status_code=200)


def test_exception_logging():
    """测试异常日志"""
    print("\n" + "="*60)
    print("测试 3: 异常日志")
    print("="*60 + "\n")
    
    try:
        result = 1 / 0
    except Exception as e:
        logger.error(
            "计算异常",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )


def test_structured_data():
    """测试结构化数据"""
    print("\n" + "="*60)
    print("测试 4: 结构化数据")
    print("="*60 + "\n")
    
    logger.info(
        "用户登录成功",
        user={
            "id": 12345,
            "username": "john_doe",
            "email": "john@example.com"
        },
        login_method="password",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0"
    )


def test_environment_output():
    """显示当前环境配置"""
    print("\n" + "="*60)
    print("当前环境配置")
    print("="*60)
    print(f"DEV 模式: {settings.DEV}")
    print(f"输出格式: {'彩色控制台 (ConsoleRenderer)' if settings.DEV else 'JSON (JSONRenderer)'}")
    print(f"应用名称: {settings.PROJECT_NAME}")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_environment_output()
    test_basic_logging()
    test_context_binding()
    test_exception_logging()
    test_structured_data()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60 + "\n")
    
    print("提示：")
    print("1. 开发环境 (DEV=True): 显示彩色易读格式")
    print("2. 生产环境 (DEV=False): 显示 JSON 格式")
    print("3. 修改 .env 文件中的 DEV 变量来切换环境")
    print()
