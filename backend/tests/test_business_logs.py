"""
测试结构化日志在业务逻辑中的应用
模拟聊天请求和性能指标记录
"""
import sys
import os
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.logger import setup_logging, get_logger
from app.core.config import settings

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)

def simulate_chat_request():
    """模拟聊天请求流程"""
    print("\n" + "="*60)
    print("模拟聊天请求流程")
    print("="*60 + "\n")
    
    # 1. 收到请求
    logger.info(
        "💬 收到聊天请求",
        user_id=12345,
        username="test_user",
        dataset_id=1,
        question_length=25,
        use_cache=True
    )
    
    # 2. 检查缓存
    cache_start = time.perf_counter()
    time.sleep(0.01)  # 模拟缓存查询
    cache_time = (time.perf_counter() - cache_start) * 1000
    
    logger.info(
        "⚡ SQL 缓存命中",
        dataset_id=1,
        cache_key="bi:sql_cache:1:abcd1234",
        cache_check_time_ms=round(cache_time, 2)
    )
    
    # 3. SQL 执行
    sql_start = time.perf_counter()
    time.sleep(0.05)  # 模拟 SQL 执行
    sql_time = (time.perf_counter() - sql_start) * 1000
    
    logger.info(
        "📊 SQL 执行完成（缓存）",
        dataset_id=1,
        sql="SELECT * FROM orders WHERE status = 'completed' LIMIT 100",
        row_count=42,
        sql_exec_time_ms=round(sql_time, 2)
    )
    
    # 4. 请求完成
    total_time = cache_time + sql_time
    logger.info(
        "✅ 请求完成（缓存）",
        dataset_id=1,
        total_time_ms=round(total_time, 2),
        from_cache=True
    )


def simulate_llm_generation():
    """模拟 LLM 生成流程"""
    print("\n" + "="*60)
    print("模拟 LLM 生成流程（无缓存）")
    print("="*60 + "\n")
    
    # 1. 开始生成 SQL
    logger.info(
        "📥 开始生成 SQL",
        dataset_id=2,
        question="查询最近7天的销售额",
        question_length=11,
        use_cache=False
    )
    
    # 2. LLM 生成
    llm_start = time.perf_counter()
    time.sleep(0.8)  # 模拟 LLM 调用
    llm_time = (time.perf_counter() - llm_start) * 1000
    
    logger.info(
        "🤖 LLM 生成 SQL 完成",
        dataset_id=2,
        llm_gen_time_ms=round(llm_time, 2),
        response_length=150
    )
    
    # 3. SQL 执行
    sql_start = time.perf_counter()
    time.sleep(0.12)  # 模拟 SQL 执行
    sql_time = (time.perf_counter() - sql_start) * 1000
    
    logger.info(
        "✅ SQL 执行成功",
        dataset_id=2,
        sql="SELECT DATE(created_at) as date, SUM(amount) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(created_at)",
        row_count=7,
        column_count=2,
        sql_exec_time_ms=round(sql_time, 2)
    )
    
    # 4. 写入缓存
    logger.info(
        "💾 SQL 已缓存",
        dataset_id=2,
        cache_key="bi:sql_cache:2:wxyz5678",
        ttl_hours=24
    )
    
    # 5. 请求完成
    total_time = llm_time + sql_time
    logger.info(
        "🎉 请求完成",
        dataset_id=2,
        total_time_ms=round(total_time, 2),
        from_cache=False
    )


def simulate_error_scenario():
    """模拟错误场景"""
    print("\n" + "="*60)
    print("模拟错误场景")
    print("="*60 + "\n")
    
    try:
        # 模拟 SQL 执行失败
        logger.error(
            "❌ SQL 执行失败",
            dataset_id=3,
            sql="SELECT * FROM non_existent_table",
            error="Table 'db.non_existent_table' doesn't exist",
            error_type="ProgrammingError",
            exc_info=False  # 这里不输出完整堆栈
        )
        
        # 模拟警告
        logger.warning(
            "⚠️ 缓存失效",
            dataset_id=3,
            reason="dataset or datasource not found"
        )
        
    except Exception as e:
        logger.error(
            "❌ 请求处理异常",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )


def main():
    print("\n" + "="*60)
    print("当前环境配置")
    print("="*60)
    print(f"DEV 模式: {settings.DEV}")
    print(f"输出格式: {'彩色控制台 (ConsoleRenderer)' if settings.DEV else 'JSON (JSONRenderer)'}")
    print("="*60 + "\n")
    
    simulate_chat_request()
    time.sleep(0.5)
    
    simulate_llm_generation()
    time.sleep(0.5)
    
    simulate_error_scenario()
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60 + "\n")
    
    print("日志特性：")
    print("✓ 自动携带 request_id（通过 Middleware 注入）")
    print("✓ 结构化数据（dataset_id, user_id, 性能指标等）")
    print("✓ 性能指标（cache_check_time_ms, llm_gen_time_ms, sql_exec_time_ms）")
    print("✓ 开发环境：彩色输出")
    print("✓ 生产环境：JSON 格式（设置 DEV=False）")
    print()


if __name__ == "__main__":
    main()
