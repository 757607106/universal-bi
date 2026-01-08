"""
简单功能测试 - 不依赖复杂计算
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_chart_recommender_import():
    """测试图表推荐器导入"""
    try:
        from app.services.chart_recommender import ChartRecommender
        print("✅ ChartRecommender 导入成功")
        
        # 测试基本功能
        import pandas as pd
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        chart_type = ChartRecommender.recommend(df, "test")
        print(f"✅ 图表推荐功能正常，推荐类型: {chart_type}")
        return True
    except Exception as e:
        print(f"❌ ChartRecommender 测试失败: {e}")
        return False


def test_query_rewriter_import():
    """测试查询重写器导入"""
    try:
        from app.services.query_rewriter import QueryRewriter
        print("✅ QueryRewriter 导入成功")
        
        # 测试should_rewrite方法
        result = QueryRewriter.should_rewrite("test", None)
        print(f"✅ 查询重写判断功能正常: {result}")
        return True
    except Exception as e:
        print(f"❌ QueryRewriter 测试失败: {e}")
        return False


def test_data_exporter_import():
    """测试数据导出器导入"""
    try:
        from app.services.data_exporter import DataExporter
        print("✅ DataExporter 导入成功")
        
        # 测试文件名生成
        filename = DataExporter.generate_filename("测试", "xlsx")
        print(f"✅ 文件名生成功能正常: {filename}")
        return True
    except Exception as e:
        print(f"❌ DataExporter 测试失败: {e}")
        return False


def test_stats_analyzer_import():
    """测试统计分析器导入"""
    try:
        from app.services.stats_analyzer import StatsAnalyzer
        print("✅ StatsAnalyzer 导入成功")
        return True
    except Exception as e:
        print(f"❌ StatsAnalyzer 测试失败: {e}")
        return False


def test_sql_generator_integration():
    """测试SQL生成器集成"""
    try:
        from app.services.vanna.sql_generator import VannaSqlGenerator
        print("✅ VannaSqlGenerator 导入成功（包含新功能）")
        return True
    except Exception as e:
        print(f"❌ VannaSqlGenerator 测试失败: {e}")
        return False


def test_chat_api_schemas():
    """测试Chat API Schema"""
    try:
        from app.schemas.chat import ChatRequest, ChatResponse
        print("✅ ChatRequest/ChatResponse Schema 导入成功")
        
        # 测试新字段
        request = ChatRequest(
            dataset_id=1,
            question="test",
            conversation_history=[{"role": "user", "content": "test"}]
        )
        print(f"✅ conversation_history 字段可用")
        
        response_data = {
            "sql": "SELECT 1",
            "columns": ["col1"],
            "rows": [{"col1": 1}],
            "chart_type": "table",
            "alternative_charts": ["bar", "line"]
        }
        response = ChatResponse(**response_data)
        print(f"✅ alternative_charts 字段可用")
        return True
    except Exception as e:
        print(f"❌ Chat API Schema 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行功能测试...")
    print("=" * 60)
    
    tests = [
        ("图表推荐器", test_chart_recommender_import),
        ("查询重写器", test_query_rewriter_import),
        ("数据导出器", test_data_exporter_import),
        ("统计分析器", test_stats_analyzer_import),
        ("SQL生成器集成", test_sql_generator_integration),
        ("Chat API Schema", test_chat_api_schemas),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- 测试: {name} ---")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

