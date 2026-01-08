"""
Vanna 重构模块测试

测试 vanna/ 子模块拆分后的各个服务功能：
- VannaInstanceManager: 实例管理
- VannaCacheService: 缓存服务
- VannaTrainingService: 训练服务
- VannaSqlGenerator: SQL 生成
- VannaTrainingDataService: 训练数据管理
- VannaAnalystService: 分析服务
- VannaManager: 外观类兼容性

运行方式:
    cd backend
    python -m pytest tests/test_vanna_refactored.py -v
    或者
    python tests/test_vanna_refactored.py
"""

import os
import sys
import asyncio
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
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


# ============================================================
# 测试 1: 模块导入测试
# ============================================================
def test_module_imports():
    """测试所有模块能否正常导入"""
    print_header("测试 1: 模块导入")

    try:
        from app.services.vanna import (
            VannaManager,
            VannaAgentManager,
            VannaLegacy,
            VannaLegacyPGVector,
            SimpleUserResolver,
            TrainingStoppedException,
            VannaInstanceManager,
            VannaCacheService,
            VannaTrainingService,
            VannaSqlGenerator,
            VannaAnalystService,
            VannaTrainingDataService,
        )
        print_pass("所有服务类导入成功")

        # 验证类存在
        assert VannaManager is not None
        assert VannaInstanceManager is not None
        assert VannaCacheService is not None
        print_pass("主要服务类验证通过")

        return True
    except Exception as e:
        print_fail(f"模块导入失败: {e}")
        return False


# ============================================================
# 测试 2: 向后兼容性导入测试
# ============================================================
def test_backward_compatible_imports():
    """测试从 vanna_manager.py 导入的向后兼容性"""
    print_header("测试 2: 向后兼容性导入")

    try:
        # 测试旧的导入方式是否仍然有效
        from app.services.vanna_manager import VannaManager
        from app.services.vanna_manager import VannaLegacy
        from app.services.vanna_manager import TrainingStoppedException

        print_pass("从 vanna_manager.py 导入成功（向后兼容）")

        # 验证是同一个类
        from app.services.vanna import VannaManager as VannaManagerNew
        assert VannaManager is VannaManagerNew
        print_pass("新旧导入指向同一类")

        return True
    except Exception as e:
        print_fail(f"向后兼容导入失败: {e}")
        return False


# ============================================================
# 测试 3: Utils 工具函数测试
# ============================================================
def test_utils_functions():
    """测试 utils.py 中的工具函数"""
    print_header("测试 3: Utils 工具函数")

    try:
        from app.services.vanna.utils import (
            clean_sql,
            is_valid_sql,
            infer_chart_type,
            serialize_dataframe,
            extract_intermediate_sql,
            is_clarification_request,
        )

        # 测试 clean_sql
        dirty_sql = "```sql\nSELECT * FROM users\n```"
        cleaned = clean_sql(dirty_sql)
        assert "SELECT * FROM users" in cleaned
        assert "```" not in cleaned
        print_pass("clean_sql: Markdown 清理成功")

        # 测试 is_valid_sql
        assert is_valid_sql("SELECT * FROM users") == True
        assert is_valid_sql("Hello, how are you?") == False
        assert is_valid_sql("SELECT id FROM orders WHERE status = 'active'") == True
        print_pass("is_valid_sql: SQL 验证正确")

        # 测试 infer_chart_type
        df_empty = pd.DataFrame()
        assert infer_chart_type(df_empty) == "table"

        df_line = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'value': [100, 200]
        })
        # 由于列名包含 'date'，应推断为 line
        assert infer_chart_type(df_line) == "line"
        print_pass("infer_chart_type: 图表类型推断正确")

        # 测试 serialize_dataframe
        from datetime import datetime, date
        from decimal import Decimal

        df_test = pd.DataFrame({
            'date': [date(2024, 1, 1)],
            'amount': [Decimal('100.50')],
            'name': ['test']
        })
        rows = serialize_dataframe(df_test)
        assert isinstance(rows[0]['date'], str)  # date 被序列化为字符串
        assert isinstance(rows[0]['amount'], float)  # Decimal 被转为 float
        print_pass("serialize_dataframe: 数据序列化正确")

        # 测试 extract_intermediate_sql
        response_with_intermediate = """我不确定您指的是哪种客户类型。
让我先查询一下：
intermediate_sql
SELECT DISTINCT customer_type FROM customers

请问您指的是哪一种？"""
        intermediate = extract_intermediate_sql(response_with_intermediate)
        assert "SELECT DISTINCT" in intermediate.upper()
        print_pass("extract_intermediate_sql: 中间 SQL 提取正确")

        # 测试 is_clarification_request
        clarification_msg = "请问您指的是哪种产品类型？我无法确定您的具体需求。"
        assert is_clarification_request(clarification_msg) == True

        normal_sql_response = "SELECT * FROM products WHERE category = 'electronics'"
        assert is_clarification_request(normal_sql_response) == False
        print_pass("is_clarification_request: 澄清请求检测正确")

        return True
    except Exception as e:
        print_fail(f"Utils 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 4: VannaInstanceManager 测试
# ============================================================
def test_instance_manager():
    """测试 VannaInstanceManager 实例管理"""
    print_header("测试 4: VannaInstanceManager")

    try:
        from app.services.vanna.instance_manager import VannaInstanceManager

        # 测试缓存清理
        VannaInstanceManager.clear_instance_cache()
        assert len(VannaInstanceManager._legacy_instances) == 0
        print_pass("clear_instance_cache: 缓存清理成功")

        # 测试缓存状态
        VannaInstanceManager._legacy_instances['test_key'] = 'test_value'
        assert len(VannaInstanceManager._legacy_instances) == 1

        VannaInstanceManager.clear_instance_cache()
        assert len(VannaInstanceManager._legacy_instances) == 0
        print_pass("实例缓存管理正常")

        return True
    except Exception as e:
        print_fail(f"VannaInstanceManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 5: VannaCacheService 测试 (Mock)
# ============================================================
def test_cache_service():
    """测试 VannaCacheService 缓存服务"""
    print_header("测试 5: VannaCacheService")

    async def run_cache_tests():
        from app.services.vanna.cache_service import VannaCacheService

        # Mock Redis 服务
        with patch('app.services.vanna.cache_service.redis_service') as mock_redis:
            mock_redis.redis_client = None  # 模拟 Redis 不可用

            # 测试 Redis 不可用时的行为
            result = await VannaCacheService.clear_cache(1)
            assert result == -1
            print_pass("clear_cache: Redis 不可用时返回 -1")

            # 测试获取缓存（Redis 不可用）
            cached = await VannaCacheService.get_cached_sql(1, "test question")
            assert cached is None
            print_pass("get_cached_sql: Redis 不可用时返回 None")

    try:
        asyncio.run(run_cache_tests())
        return True
    except Exception as e:
        print_fail(f"VannaCacheService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 6: VannaTrainingDataService 测试
# ============================================================
def test_training_data_service():
    """测试 VannaTrainingDataService 训练数据服务"""
    print_header("测试 6: VannaTrainingDataService")

    try:
        from app.services.vanna.training_data_service import VannaTrainingDataService
        from app.services.vanna.instance_manager import VannaInstanceManager

        # Mock ChromaDB 客户端
        with patch.object(VannaInstanceManager, '_get_global_chroma_client') as mock_client:
            mock_collection = MagicMock()
            mock_collection.get.return_value = {
                'ids': ['id1', 'id2'],
                'documents': ['SELECT * FROM users', 'CREATE TABLE products (id INT)'],
                'metadatas': [{'question': '查询所有用户'}, {}]
            }

            mock_chroma = MagicMock()
            mock_chroma.get_collection.return_value = mock_collection
            mock_client.return_value = mock_chroma

            # 测试获取训练数据
            result = VannaTrainingDataService.get_training_data(1, page=1, page_size=20)

            assert 'total' in result
            assert 'items' in result
            assert 'page' in result
            print_pass("get_training_data: 返回结构正确")

            # 验证分页参数
            assert result['page'] == 1
            assert result['page_size'] == 20
            print_pass("get_training_data: 分页参数正确")

        return True
    except Exception as e:
        print_fail(f"VannaTrainingDataService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 7: VannaAnalystService 测试 (Mock)
# ============================================================
def test_analyst_service():
    """测试 VannaAnalystService 分析服务"""
    print_header("测试 7: VannaAnalystService")

    try:
        from app.services.vanna.analyst_service import VannaAnalystService
        from app.services.vanna.instance_manager import VannaInstanceManager

        # 测试空数据处理
        result = VannaAnalystService.generate_summary("test", None, 1)
        assert "数据为空" in result
        print_pass("generate_summary: 空数据处理正确")

        result = VannaAnalystService.generate_data_insight("test", "SELECT 1", pd.DataFrame(), 1)
        assert "数据为空" in result
        print_pass("generate_data_insight: 空数据处理正确")

        # Mock Vanna 实例测试
        with patch.object(VannaInstanceManager, 'get_legacy_vanna') as mock_get_vanna:
            mock_vn = MagicMock()
            mock_vn.submit_prompt.return_value = "这是一个测试总结，数据显示销售额增长了20%。"
            mock_get_vanna.return_value = mock_vn

            # 测试正常数据
            df = pd.DataFrame({
                'product': ['A', 'B', 'C'],
                'sales': [100, 200, 150]
            })

            result = VannaAnalystService.generate_summary("产品销售情况", df, 1)
            assert len(result) > 0
            assert "总结生成失败" not in result
            print_pass("generate_summary: 正常数据生成成功")

        return True
    except Exception as e:
        print_fail(f"VannaAnalystService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 8: VannaManager Facade 测试
# ============================================================
def test_facade_methods():
    """测试 VannaManager 外观类方法代理"""
    print_header("测试 8: VannaManager Facade")

    try:
        from app.services.vanna.facade import VannaManager
        from app.services.vanna.instance_manager import VannaInstanceManager
        from app.services.vanna.cache_service import VannaCacheService
        from app.services.vanna.training_data_service import VannaTrainingDataService

        # 验证 Facade 方法存在
        assert hasattr(VannaManager, 'get_legacy_vanna')
        assert hasattr(VannaManager, 'get_agent')
        assert hasattr(VannaManager, 'delete_collection')
        assert hasattr(VannaManager, 'clear_instance_cache')
        print_pass("实例管理方法存在")

        assert hasattr(VannaManager, 'clear_cache_async')
        assert hasattr(VannaManager, 'clear_cache')
        print_pass("缓存服务方法存在")

        assert hasattr(VannaManager, 'train_dataset')
        assert hasattr(VannaManager, 'train_dataset_async')
        assert hasattr(VannaManager, 'train_term')
        assert hasattr(VannaManager, 'train_term_async')
        assert hasattr(VannaManager, 'train_relationships')
        assert hasattr(VannaManager, 'train_relationships_async')
        assert hasattr(VannaManager, 'train_qa')
        assert hasattr(VannaManager, 'train_qa_async')
        print_pass("训练服务方法存在")

        assert hasattr(VannaManager, 'generate_result')
        print_pass("SQL 生成方法存在")

        assert hasattr(VannaManager, 'generate_summary')
        assert hasattr(VannaManager, 'generate_data_insight')
        assert hasattr(VannaManager, 'analyze_relationships')
        print_pass("分析服务方法存在")

        assert hasattr(VannaManager, 'get_training_data')
        assert hasattr(VannaManager, 'remove_training_data')
        assert hasattr(VannaManager, 'remove_training_data_async')
        print_pass("训练数据服务方法存在")

        # 测试方法代理
        with patch.object(VannaInstanceManager, 'clear_instance_cache') as mock_clear:
            VannaManager.clear_instance_cache(1)
            mock_clear.assert_called_once_with(1)
            print_pass("方法正确代理到子服务")

        return True
    except Exception as e:
        print_fail(f"VannaManager Facade 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 测试 9: TrainingStoppedException 测试
# ============================================================
def test_training_stopped_exception():
    """测试 TrainingStoppedException 自定义异常"""
    print_header("测试 9: TrainingStoppedException")

    try:
        from app.services.vanna.base import TrainingStoppedException

        # 测试异常可以被抛出和捕获
        try:
            raise TrainingStoppedException("训练被用户中断")
        except TrainingStoppedException as e:
            assert "训练被用户中断" in str(e)
            print_pass("异常抛出和捕获正常")

        # 验证是 Exception 子类
        assert issubclass(TrainingStoppedException, Exception)
        print_pass("TrainingStoppedException 是 Exception 子类")

        return True
    except Exception as e:
        print_fail(f"TrainingStoppedException 测试失败: {e}")
        return False


# ============================================================
# 测试 10: VannaLegacy 基类测试 (Mock)
# ============================================================
def test_vanna_legacy_base():
    """测试 VannaLegacy 基类初始化"""
    print_header("测试 10: VannaLegacy 基类")

    try:
        from app.services.vanna.base import VannaLegacy

        # Mock ChromaDB 客户端
        mock_chroma_client = MagicMock()
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        # 初始化 VannaLegacy
        config = {
            'api_key': 'test_key',
            'model': 'test_model',
            'n_results': 10,
            'collection_name': 'test_collection',
            'api_base': 'https://test.api.com'
        }

        vn = VannaLegacy(config=config, chroma_client=mock_chroma_client)

        # 验证属性
        assert vn.model == 'test_model'
        assert vn.n_results == 10
        assert vn.chroma_client == mock_chroma_client
        print_pass("VannaLegacy 初始化成功")

        # 验证 VannaBase 需要的属性
        assert hasattr(vn, 'run_sql_is_set')
        assert hasattr(vn, 'static_documentation')
        assert hasattr(vn, 'dialect')
        assert hasattr(vn, 'language')
        assert hasattr(vn, 'max_tokens')
        print_pass("VannaBase 属性初始化正确")

        # 验证 ChromaDB 相关属性
        assert hasattr(vn, 'n_results_sql')
        assert hasattr(vn, 'n_results_documentation')
        assert hasattr(vn, 'n_results_ddl')
        print_pass("ChromaDB 属性初始化正确")

        return True
    except Exception as e:
        print_fail(f"VannaLegacy 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 主测试入口
# ============================================================
def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(" Vanna 重构模块测试")
    print(f"{'='*60}{Colors.RESET}")

    tests = [
        ("模块导入", test_module_imports),
        ("向后兼容性导入", test_backward_compatible_imports),
        ("Utils 工具函数", test_utils_functions),
        ("VannaInstanceManager", test_instance_manager),
        ("VannaCacheService", test_cache_service),
        ("VannaTrainingDataService", test_training_data_service),
        ("VannaAnalystService", test_analyst_service),
        ("VannaManager Facade", test_facade_methods),
        ("TrainingStoppedException", test_training_stopped_exception),
        ("VannaLegacy 基类", test_vanna_legacy_base),
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
    print(" 测试总结")
    print(f"{'='*60}{Colors.RESET}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {name}: {status}")

    print(f"\n{Colors.BOLD}通过: {passed_count}/{total_count}{Colors.RESET}")

    if passed_count == total_count:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
