"""
智能图表推荐服务 - 根据数据形态自动推荐最佳图表类型
"""
import pandas as pd
from typing import Dict, Any, List
from app.core.logger import get_logger

logger = get_logger(__name__)


class ChartRecommender:
    """智能图表推荐器"""
    
    # 图表类型常量
    CHART_LINE = "line"       # 折线图
    CHART_BAR = "bar"         # 柱状图
    CHART_PIE = "pie"         # 饼图
    CHART_TABLE = "table"     # 表格
    CHART_SCATTER = "scatter" # 散点图
    CHART_AREA = "area"       # 面积图
    
    @staticmethod
    def recommend(df: pd.DataFrame, question: str = "") -> str:
        """
        根据DataFrame的数据形态推荐最佳图表类型
        
        推荐规则：
        1. 包含日期/时间列 + 数值列 -> 折线图/面积图（趋势类）
        2. 分类列 + 数值列，且分类数 < 8 -> 饼图（构成类）
        3. 分类列 + 数值列，且分类数 >= 8 -> 柱状图（对比类）
        4. 多个数值列，无明显分类 -> 散点图或表格
        5. 多维度无聚合 -> 表格（明细类）
        
        Args:
            df: 数据框
            question: 用户问题（用于辅助判断）
            
        Returns:
            str: 推荐的图表类型
        """
        if df is None or df.empty:
            return ChartRecommender.CHART_TABLE
        
        # 分析数据结构
        analysis = ChartRecommender._analyze_dataframe(df)
        
        # 检查用户问题中的关键词
        question_lower = question.lower()
        
        # 强制推荐：用户明确指定图表类型
        if any(keyword in question_lower for keyword in ['趋势', '变化', '增长', '下降', '走势']):
            if analysis['has_time_column']:
                return ChartRecommender.CHART_LINE
        
        if any(keyword in question_lower for keyword in ['占比', '比例', '分布', '构成']):
            if analysis['categorical_count'] > 0 and analysis['numeric_count'] > 0:
                if analysis['unique_categories'] <= 8:
                    return ChartRecommender.CHART_PIE
        
        if any(keyword in question_lower for keyword in ['对比', '比较', '排名', 'top']):
            if analysis['categorical_count'] > 0 and analysis['numeric_count'] > 0:
                return ChartRecommender.CHART_BAR
        
        # 自动推荐逻辑
        chart_type = ChartRecommender._auto_recommend(analysis, df)
        
        logger.info(
            "Chart recommendation completed",
            recommended_chart=chart_type,
            has_time=analysis['has_time_column'],
            categorical_count=analysis['categorical_count'],
            numeric_count=analysis['numeric_count'],
            unique_categories=analysis['unique_categories'],
            row_count=len(df)
        )
        
        return chart_type
    
    @staticmethod
    def _analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析DataFrame的结构特征
        
        Returns:
            Dict: {
                'has_time_column': bool,
                'time_columns': List[str],
                'categorical_columns': List[str],
                'numeric_columns': List[str],
                'categorical_count': int,
                'numeric_count': int,
                'unique_categories': int  # 最大类别数
            }
        """
        analysis = {
            'has_time_column': False,
            'time_columns': [],
            'categorical_columns': [],
            'numeric_columns': [],
            'categorical_count': 0,
            'numeric_count': 0,
            'unique_categories': 0
        }
        
        for col in df.columns:
            # 检查是否是日期/时间列
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                analysis['has_time_column'] = True
                analysis['time_columns'].append(col)
            elif df[col].dtype == 'object':
                # 尝试解析为日期
                try:
                    sample = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
                    if sample:
                        pd.to_datetime(sample)
                        analysis['has_time_column'] = True
                        analysis['time_columns'].append(col)
                        continue
                except:
                    pass
                
                # 分类列
                unique_count = df[col].nunique()
                if unique_count < len(df) * 0.5:  # 唯一值 < 50%认为是分类列
                    analysis['categorical_columns'].append(col)
                    analysis['categorical_count'] += 1
                    analysis['unique_categories'] = max(analysis['unique_categories'], unique_count)
            
            # 数值列
            elif pd.api.types.is_numeric_dtype(df[col]):
                analysis['numeric_columns'].append(col)
                analysis['numeric_count'] += 1
        
        return analysis
    
    @staticmethod
    def _auto_recommend(analysis: Dict[str, Any], df: pd.DataFrame) -> str:
        """
        基于分析结果自动推荐图表类型
        
        Args:
            analysis: 数据分析结果
            df: 原始数据框
            
        Returns:
            str: 推荐的图表类型
        """
        # 规则1：趋势类 - 包含时间列 + 数值列
        if analysis['has_time_column'] and analysis['numeric_count'] > 0:
            # 如果数值列只有1个，用折线图；多个用面积图
            if analysis['numeric_count'] == 1:
                return ChartRecommender.CHART_LINE
            else:
                return ChartRecommender.CHART_AREA
        
        # 规则2：构成类 - 分类列 + 数值列，且分类数 < 8
        if analysis['categorical_count'] > 0 and analysis['numeric_count'] > 0:
            if analysis['unique_categories'] <= 7:
                return ChartRecommender.CHART_PIE
            else:
                # 规则3：对比类 - 分类数 >= 8，用柱状图
                return ChartRecommender.CHART_BAR
        
        # 规则4：只有数值列，无分类
        if analysis['numeric_count'] >= 2 and analysis['categorical_count'] == 0:
            # 散点图（适合展示两个数值变量的关系）
            if analysis['numeric_count'] == 2 and len(df) < 1000:
                return ChartRecommender.CHART_SCATTER
            else:
                return ChartRecommender.CHART_TABLE
        
        # 规则5：明细类 - 多维度，无明显聚合
        if len(df) > 20 and len(df.columns) >= 4:
            return ChartRecommender.CHART_TABLE
        
        # 规则6：数据量很大
        if len(df) > 100:
            return ChartRecommender.CHART_TABLE
        
        # 默认：柱状图（通用性最强）
        if analysis['categorical_count'] > 0 or analysis['numeric_count'] > 0:
            return ChartRecommender.CHART_BAR
        
        # 兜底：表格
        return ChartRecommender.CHART_TABLE
    
    @staticmethod
    def get_alternative_charts(df: pd.DataFrame, current_chart: str) -> List[str]:
        """
        获取可选的备用图表类型
        
        Args:
            df: 数据框
            current_chart: 当前图表类型
            
        Returns:
            List[str]: 可选的图表类型列表
        """
        if df is None or df.empty:
            return [ChartRecommender.CHART_TABLE]
        
        analysis = ChartRecommender._analyze_dataframe(df)
        alternatives = []
        
        # 时间序列数据可选：折线图、柱状图、面积图
        if analysis['has_time_column'] and analysis['numeric_count'] > 0:
            alternatives.extend([
                ChartRecommender.CHART_LINE,
                ChartRecommender.CHART_BAR,
                ChartRecommender.CHART_AREA
            ])
        
        # 分类数据可选：柱状图、饼图
        if analysis['categorical_count'] > 0 and analysis['numeric_count'] > 0:
            alternatives.extend([
                ChartRecommender.CHART_BAR,
                ChartRecommender.CHART_PIE
            ])
        
        # 数值数据可选：散点图、柱状图
        if analysis['numeric_count'] >= 2:
            alternatives.extend([
                ChartRecommender.CHART_SCATTER,
                ChartRecommender.CHART_BAR
            ])
        
        # 表格总是可选
        alternatives.append(ChartRecommender.CHART_TABLE)
        
        # 去重并移除当前图表
        alternatives = list(set(alternatives))
        if current_chart in alternatives:
            alternatives.remove(current_chart)
        
        return alternatives[:3]  # 最多返回3个备选

