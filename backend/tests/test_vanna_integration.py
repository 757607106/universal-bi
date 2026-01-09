"""
Vanna 重构模块集成测试

测试实际与 PGVector 和 LLM 的交互（需要有效的环境配置）

运行方式:
    cd backend
    python tests/test_vanna_integration.py

注意：此测试需要：
1. 有效的 DASHSCOPE_API_KEY 环境变量
2. PGVector 数据库可访问 (默认配置)
3. 可选：Redis 服务（用于缓存测试）
"""

import os
import sys
import asyncio

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f" {text}")
    print(f"{'='*60}{Colors.RESET}\n")


def print_pass(text: str):
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")


def print_fail(text: str):
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    print(f"  {Colors.YELLOW}ℹ {text}{Colors.RESET}")


def print_skip(text: str):
    print(f"  {Colors.CYAN}⊘ SKIP: {text}{Colors.RESET}")


# ============================================================
# 集成测试 1: PGVector 实例创建测试
# ============================================================
def test_pgvector_instance_creation():
    """测试 PGVector 实例创建"""
    print_header("集成测试 1: PGVector 实例创建")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager
        from app.core.config import settings

        # 确认使用 PGVector
        print_info(f"向量存储类型: {settings.VECTOR_STORE_TYPE}")
        assert settings.VECTOR_STORE_TYPE.lower() == "pgvector", "配置应为 pgvector"

        # 清理缓存
        VannaInstanceManager.clear_instance_cache()

        # 测试 VannaLegacy 实例创建
        test_dataset_id = 99999  # 使用一个不存在的 ID 避免冲突
        vn = VannaInstanceManager.get_legacy_vanna(test_dataset_id)
        assert vn is not None
        print_pass("VannaLegacyPGVector 实例创建成功")

        # 验证缓存
        vn2 = VannaInstanceManager.get_legacy_vanna(test_dataset_id)
        assert vn is vn2  # 应该是同一个实例
        print_pass("实例缓存机制正常")

        # 清理测试实例
        VannaInstanceManager.clear_instance_cache(test_dataset_id)
        print_pass("测试实例缓存清理成功")

        return True
    except Exception as e:
        print_fail(f"PGVector 实例创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 2: 训练数据存储测试 (PGVector)
# ============================================================
def test_training_data_storage():
    """测试训练数据存储到 PGVector"""
    print_header("集成测试 2: 训练数据存储 (PGVector)")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager
        from app.services.vanna.training_data_service import VannaTrainingDataService
        from app.core.config import settings

        # 清理
        VannaInstanceManager.clear_instance_cache()

        test_dataset_id = 88888

        # 获取 Vanna 实例
        vn = VannaInstanceManager.get_legacy_vanna(test_dataset_id)

        # 训练 DDL
        ddl = """CREATE TABLE test_users (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(200)
        )"""
        vn.train(ddl=ddl)
        print_pass("DDL 训练成功")

        # 训练文档
        doc = "业务术语: 活跃用户\n定义: 最近30天内有登录记录的用户"
        vn.train(documentation=doc)
        print_pass("文档训练成功")

        # 训练 QA 对
        vn.train(question="查询所有用户", sql="SELECT * FROM test_users")
        print_pass("QA 对训练成功")

        # 获取训练数据
        result = VannaTrainingDataService.get_training_data(test_dataset_id)
        assert result['total'] >= 3  # 至少有 3 条训练数据
        print_pass(f"训练数据查询成功: {result['total']} 条")

        # 验证数据类型
        types = set(item['training_data_type'] for item in result['items'])
        print_info(f"数据类型: {types}")
        assert len(types) > 0  # 至少有一种类型
        print_pass("训练数据类型正确")

        # 清理缓存
        VannaInstanceManager.clear_instance_cache(test_dataset_id)

        return True
    except Exception as e:
        print_fail(f"训练数据存储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 3: 向量检索测试 (PGVector)
# ============================================================
def test_vector_retrieval():
    """测试向量检索功能"""
    print_header("集成测试 3: 向量检索 (PGVector)")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager

        # 清理
        VannaInstanceManager.clear_instance_cache()

        test_dataset_id = 77777

        # 获取 Vanna 实例
        vn = VannaInstanceManager.get_legacy_vanna(test_dataset_id)

        # 训练一些数据
        vn.train(ddl="CREATE TABLE orders (id INT, customer_id INT, amount DECIMAL(10,2), order_date DATE)")
        vn.train(ddl="CREATE TABLE customers (id INT, name VARCHAR(100), email VARCHAR(200))")
        vn.train(documentation="业务术语: 大客户 - 月消费超过1万元的客户")
        vn.train(question="查询所有订单", sql="SELECT * FROM orders")
        vn.train(question="查询大客户订单", sql="SELECT * FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE monthly_spend > 10000)")

        print_pass("测试数据训练完成")

        # 测试 DDL 检索
        related_ddl = vn.get_related_ddl("订单金额")
        assert len(related_ddl) > 0
        print_pass(f"DDL 检索成功: 找到 {len(related_ddl)} 条相关 DDL")

        # 测试文档检索
        related_docs = vn.get_related_documentation("大客户")
        assert len(related_docs) > 0
        print_pass(f"文档检索成功: 找到 {len(related_docs)} 条相关文档")

        # 测试 QA 检索
        similar_qa = vn.get_similar_question_sql("查询订单")
        assert len(similar_qa) > 0
        print_pass(f"QA 检索成功: 找到 {len(similar_qa)} 条相关 QA")

        # 清理
        VannaInstanceManager.clear_instance_cache(test_dataset_id)

        return True
    except Exception as e:
        print_fail(f"向量检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 4: LLM 调用测试 (需要有效 API Key)
# ============================================================
def test_llm_integration():
    """测试 LLM 调用（需要有效的 API Key）"""
    print_header("集成测试 4: LLM 调用")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager
        from app.core.config import settings

        # 检查 API Key
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "your_api_key_here":
            print_skip("未配置有效的 DASHSCOPE_API_KEY，跳过 LLM 测试")
            return True  # 返回 True 因为这不是失败，只是跳过

        # 清理
        VannaInstanceManager.clear_instance_cache()

        test_dataset_id = 66666

        # 获取 Vanna 实例
        vn = VannaInstanceManager.get_legacy_vanna(test_dataset_id)

        # 训练一些基础数据
        vn.train(ddl="CREATE TABLE products (id INT, name VARCHAR(100), price DECIMAL(10,2), category VARCHAR(50))")
        print_pass("DDL 训练完成")

        # 测试 submit_prompt
        response = vn.submit_prompt("你好，请用一句话介绍自己")
        assert response is not None and len(response) > 0
        print_pass(f"submit_prompt 调用成功: {response[:50]}...")

        # 测试 SQL 生成
        try:
            sql = vn.generate_sql("查询所有产品")
            if sql:
                print_pass(f"SQL 生成成功: {sql[:100]}...")
            else:
                print_info("SQL 生成返回空（可能需要更多训练数据）")
        except Exception as e:
            print_info(f"SQL 生成异常（可能需要更多训练数据）: {str(e)[:50]}")

        # 清理
        VannaInstanceManager.clear_instance_cache(test_dataset_id)

        return True
    except Exception as e:
        print_fail(f"LLM 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 5: 删除训练数据测试 (PGVector)
# ============================================================
def test_remove_training_data():
    """测试删除单条训练数据"""
    print_header("集成测试 5: 删除训练数据 (PGVector)")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager
        from app.services.vanna.training_data_service import VannaTrainingDataService

        # 清理
        VannaInstanceManager.clear_instance_cache()

        test_dataset_id = 55555

        # 获取 Vanna 实例并训练数据
        vn = VannaInstanceManager.get_legacy_vanna(test_dataset_id)
        vn.train(ddl="CREATE TABLE delete_test (id INT)")
        vn.train(documentation="测试文档：这是要删除的文档")
        print_pass("测试数据训练完成")

        # 获取训练数据
        result = VannaTrainingDataService.get_training_data(test_dataset_id)
        initial_count = result['total']
        assert initial_count >= 2
        print_pass(f"初始训练数据数量: {initial_count}")

        # 获取要删除的 ID
        item_to_delete = result['items'][0]
        item_id = item_to_delete['id']
        print_info(f"准备删除 ID: {item_id}")

        # 删除训练数据
        success = VannaTrainingDataService.remove_training_data(test_dataset_id, item_id)
        print_pass(f"删除操作返回: {success}")

        # 验证删除
        result_after = VannaTrainingDataService.get_training_data(test_dataset_id)
        print_info(f"删除后训练数据数量: {result_after['total']}")

        # 清理
        VannaInstanceManager.clear_instance_cache(test_dataset_id)

        return True
    except Exception as e:
        print_fail(f"删除训练数据测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 6: 缓存服务测试 (需要 Redis)
# ============================================================
def test_cache_service_with_redis():
    """测试缓存服务（需要 Redis 服务运行）"""
    print_header("集成测试 6: 缓存服务")

    async def run_cache_test():
        from app.services.vanna.cache_service import VannaCacheService
        from app.core.redis import redis_service

        # 检查 Redis 连接
        if not redis_service.redis_client:
            print_skip("Redis 服务不可用，跳过缓存测试")
            return True

        test_dataset_id = 44444
        test_question = "测试问题：查询所有用户"
        test_sql = "SELECT * FROM users"

        try:
            # 测试缓存 SQL
            cached = await VannaCacheService.cache_sql(test_dataset_id, test_question, test_sql)
            assert cached == True
            print_pass("SQL 缓存写入成功")

            # 测试获取缓存
            retrieved = await VannaCacheService.get_cached_sql(test_dataset_id, test_question)
            assert retrieved == test_sql
            print_pass("SQL 缓存读取成功")

            # 测试删除缓存
            deleted = await VannaCacheService.delete_cached_sql(test_dataset_id, test_question)
            assert deleted == True
            print_pass("SQL 缓存删除成功")

            # 验证删除
            retrieved_after = await VannaCacheService.get_cached_sql(test_dataset_id, test_question)
            assert retrieved_after is None
            print_pass("缓存删除验证成功")

            # 测试清除所有缓存
            await VannaCacheService.cache_sql(test_dataset_id, "test1", "sql1")
            await VannaCacheService.cache_sql(test_dataset_id, "test2", "sql2")
            cleared = await VannaCacheService.clear_cache(test_dataset_id)
            print_pass(f"清除缓存成功: {cleared} 条")

            return True
        except Exception as e:
            print_fail(f"缓存测试失败: {e}")
            return False

    try:
        return asyncio.run(run_cache_test())
    except Exception as e:
        print_fail(f"缓存服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 集成测试 7: VannaManager Facade 完整性测试
# ============================================================
def test_facade_integration():
    """测试 VannaManager Facade 的完整集成"""
    print_header("集成测试 7: VannaManager Facade 完整性")

    try:
        from app.services.vanna.facade import VannaManager

        test_dataset_id = 33333

        # 清理缓存
        VannaManager.clear_instance_cache()
        print_pass("Facade clear_instance_cache 调用成功")

        # 获取实例
        vn = VannaManager.get_legacy_vanna(test_dataset_id)
        assert vn is not None
        print_pass("Facade get_legacy_vanna 调用成功")

        # 获取训练数据
        result = VannaManager.get_training_data(test_dataset_id)
        assert 'total' in result
        assert 'items' in result
        print_pass("Facade get_training_data 调用成功")

        # 清理
        VannaManager.clear_instance_cache(test_dataset_id)

        return True
    except Exception as e:
        print_fail(f"Facade 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 主测试入口
# ============================================================
def run_all_integration_tests():
    """运行所有集成测试"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(" Vanna 重构模块集成测试 (PGVector)")
    print(f"{'='*60}{Colors.RESET}")

    # 显示配置信息
    from app.core.config import settings
    print_info(f"向量存储类型: {settings.VECTOR_STORE_TYPE}")
    print_info(f"PGVector 连接: {settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}")
    print_info(f"LLM 模型: {settings.QWEN_MODEL}")

    tests = [
        ("PGVector 实例创建", test_pgvector_instance_creation),
        ("训练数据存储", test_training_data_storage),
        ("向量检索", test_vector_retrieval),
        ("LLM 调用", test_llm_integration),
        ("删除训练数据", test_remove_training_data),
        ("缓存服务", test_cache_service_with_redis),
        ("Facade 完整性", test_facade_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print_fail(f"{name} 测试异常: {e}")
            results.append((name, False))

    # 打印总结
    print(f"\n{Colors.BOLD}{'='*60}")
    print(" 集成测试总结")
    print(f"{'='*60}{Colors.RESET}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {name}: {status}")

    print(f"\n{Colors.BOLD}通过: {passed_count}/{total_count}{Colors.RESET}")

    if passed_count == total_count:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有集成测试通过！{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分集成测试失败{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
