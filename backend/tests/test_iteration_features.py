"""
迭代功能集成测试
测试阶段三和阶段四的新功能
"""
import pytest
import pandas as pd
from app.services.chart_recommender import ChartRecommender
from app.services.query_rewriter import QueryRewriter
from app.services.data_exporter import DataExporter
from app.services.stats_analyzer import StatsAnalyzer


class TestChartRecommender:
    """测试智能图表推荐器"""
    
    def test_recommend_line_chart_with_time_series(self):
        """测试时间序列数据推荐折线图"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'sales': [100, 120, 130, 125, 140, 150, 160, 155, 170, 180]
        })
        
        chart_type = ChartRecommender.recommend(df, "查询销售趋势")
        assert chart_type == "line"
    
    def test_recommend_pie_chart_for_composition(self):
        """测试构成类数据推荐饼图"""
        df = pd.DataFrame({
            'category': ['A', 'B', 'C', 'D'],
            'value': [25, 35, 20, 20]
        })
        
        chart_type = ChartRecommender.recommend(df, "查询销售占比")
        assert chart_type == "pie"
    
    def test_recommend_bar_chart_for_comparison(self):
        """测试对比类数据推荐柱状图"""
        df = pd.DataFrame({
            'city': ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆'],
            'sales': [1000, 1200, 800, 900, 700, 650, 600, 550, 500, 450]
        })
        
        chart_type = ChartRecommender.recommend(df, "查询各城市销售对比")
        assert chart_type == "bar"
    
    def test_recommend_table_for_detailed_data(self):
        """测试明细数据推荐表格"""
        df = pd.DataFrame({
            'order_id': range(1, 101),
            'customer': [f'customer_{i}' for i in range(100)],
            'amount': [100 * i for i in range(1, 101)],
            'date': pd.date_range('2024-01-01', periods=100)
        })
        
        chart_type = ChartRecommender.recommend(df, "查询订单明细")
        assert chart_type == "table"
    
    def test_get_alternative_charts(self):
        """测试获取备用图表类型"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'sales': [100, 120, 130, 125, 140, 150, 160, 155, 170, 180]
        })
        
        alternatives = ChartRecommender.get_alternative_charts(df, "line")
        assert len(alternatives) > 0
        assert "line" not in alternatives
        assert "table" in alternatives


class TestQueryRewriter:
    """测试查询重写器"""
    
    def test_rewrite_with_history(self):
        """测试基于历史的查询重写"""
        history = [
            {"role": "user", "content": "查询上个月的销售额"},
            {"role": "assistant", "content": "已为您查询，总销售额为100万元"}
        ]
        
        current_query = "按城市拆分"
        rewritten = QueryRewriter.rewrite_query(current_query, history)
        
        # 重写后的查询应该包含原始上下文
        assert len(rewritten) > len(current_query)
        print(f"Original: {current_query}")
        print(f"Rewritten: {rewritten}")
    
    def test_no_rewrite_for_long_query(self):
        """测试长查询不需要重写"""
        history = [
            {"role": "user", "content": "查询销售额"},
            {"role": "assistant", "content": "结果"}
        ]
        
        current_query = "查询2024年第一季度所有产品的销售额和利润率"
        rewritten = QueryRewriter.rewrite_query(current_query, history)
        
        # 长查询应该保持不变
        assert rewritten == current_query
    
    def test_should_rewrite_detection(self):
        """测试是否需要重写的判断"""
        history = [
            {"role": "user", "content": "查询销售额"},
            {"role": "assistant", "content": "结果"}
        ]
        
        # 短查询且包含追问词 -> 需要重写
        assert QueryRewriter.should_rewrite("按城市拆分", history) == True
        
        # 长查询 -> 不需要重写
        assert QueryRewriter.should_rewrite("查询2024年所有产品的销售额", history) == False
        
        # 无历史 -> 不需要重写
        assert QueryRewriter.should_rewrite("按城市拆分", None) == False


class TestDataExporter:
    """测试数据导出器"""
    
    def test_export_to_excel(self):
        """测试Excel导出"""
        data = [
            {"name": "张三", "age": 25, "city": "北京"},
            {"name": "李四", "age": 30, "city": "上海"},
            {"name": "王五", "age": 28, "city": "广州"}
        ]
        columns = ["name", "age", "city"]
        
        excel_bytes, filename = DataExporter.export_to_excel(data, columns, "测试数据")
        
        assert len(excel_bytes) > 0
        assert filename.endswith(".xlsx")
        assert "测试数据" in filename
    
    def test_export_to_csv(self):
        """测试CSV导出"""
        data = [
            {"name": "张三", "age": 25, "city": "北京"},
            {"name": "李四", "age": 30, "city": "上海"}
        ]
        columns = ["name", "age", "city"]
        
        csv_bytes, filename = DataExporter.export_to_csv(data, columns, "测试数据")
        
        assert len(csv_bytes) > 0
        assert filename.endswith(".csv")
        assert "测试数据" in filename
    
    def test_generate_filename(self):
        """测试文件名生成"""
        question = "查询上个月的销售额"
        filename = DataExporter.generate_filename(question, "xlsx")
        
        assert filename.endswith(".xlsx")
        assert "查询上个月的销售额" in filename or "查询" in filename


class TestStatsAnalyzer:
    """测试统计分析引擎"""
    
    def test_analyze_numeric_columns(self):
        """测试数值列统计"""
        df = pd.DataFrame({
            'sales': [100, 120, 130, 125, 140, 150, 160, 155, 170, 180],
            'profit': [20, 25, 28, 26, 30, 32, 35, 33, 38, 40]
        })
        
        stats = StatsAnalyzer.analyze(df, "销售数据")
        
        assert 'numeric_stats' in stats
        assert 'sales' in stats['numeric_stats']
        assert 'mean' in stats['numeric_stats']['sales']
        assert stats['numeric_stats']['sales']['mean'] > 0
    
    def test_analyze_time_series(self):
        """测试时间序列分析"""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'sales': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
        })
        
        stats = StatsAnalyzer.analyze(df, "销售趋势")
        
        assert 'time_series_stats' in stats
        if stats['time_series_stats']:
            # 应该有增长率统计
            ts_stat = list(stats['time_series_stats'].values())[0]
            assert 'overall_growth' in ts_stat
            assert ts_stat['overall_growth'] > 0  # 数据是增长的
    
    def test_detect_anomalies(self):
        """测试异常检测"""
        df = pd.DataFrame({
            'value': [100, 105, 98, 102, 500, 103, 99, 101, 104, 106]  # 500是异常值
        })
        
        stats = StatsAnalyzer.analyze(df, "异常检测")
        
        assert 'anomalies' in stats
        # 应该检测到异常值
        if stats['anomalies']:
            anomaly = stats['anomalies'][0]
            assert anomaly['count'] > 0
            assert anomaly['column'] == 'value'


# 运行测试的便捷函数
def run_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()

