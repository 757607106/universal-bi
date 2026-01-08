"""
统计分析引擎 - 自动化数据统计特征计算
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


class StatsAnalyzer:
    """统计分析器 - 计算DataFrame的统计特征"""
    
    @staticmethod
    def analyze(df: pd.DataFrame, question: str = "") -> Dict[str, Any]:
        """
        对DataFrame进行全面的统计分析
        
        Args:
            df: 数据框
            question: 用户的原始问题（用于上下文）
            
        Returns:
            Dict: 统计摘要
        """
        if df.empty:
            return {
                "total_rows": 0,
                "total_columns": 0,
                "numeric_stats": {},
                "time_series_stats": {},
                "anomalies": [],
                "summary": "数据为空"
            }
        
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_stats": StatsAnalyzer._analyze_numeric_columns(df),
            "time_series_stats": StatsAnalyzer._analyze_time_series(df),
            "anomalies": StatsAnalyzer._detect_anomalies(df),
            "categorical_stats": StatsAnalyzer._analyze_categorical_columns(df)
        }
        
        # 生成文本摘要
        stats["summary"] = StatsAnalyzer._generate_summary(stats, df)
        
        logger.info(
            "Statistical analysis completed",
            rows=stats["total_rows"],
            columns=stats["total_columns"],
            numeric_columns=len(stats["numeric_stats"]),
            time_series_columns=len(stats["time_series_stats"]),
            anomalies=len(stats["anomalies"])
        )
        
        return stats
    
    @staticmethod
    def _analyze_numeric_columns(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        分析数值列的统计特征
        
        Returns:
            Dict: {列名: {指标: 值}}
        """
        numeric_stats = {}
        
        # 获取数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            stats = {
                "count": int(len(series)),
                "sum": float(series.sum()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std()),
                "variance": float(series.var()),
                "min": float(series.min()),
                "max": float(series.max()),
                "q25": float(series.quantile(0.25)),
                "q75": float(series.quantile(0.75))
            }
            
            # 计算变异系数（CV）- 衡量波动性
            if stats["mean"] != 0:
                stats["cv"] = abs(stats["std"] / stats["mean"])
            else:
                stats["cv"] = 0
            
            numeric_stats[col] = stats
        
        return numeric_stats
    
    @staticmethod
    def _analyze_time_series(df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析时间序列数据，计算环比(MoM)和同比(YoY)
        
        Returns:
            Dict: 时间序列统计信息
        """
        time_series_stats = {}
        
        # 尝试识别日期列
        date_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_cols.append(col)
            elif df[col].dtype == 'object':
                # 尝试解析为日期
                try:
                    pd.to_datetime(df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None)
                    date_cols.append(col)
                except:
                    pass
        
        if not date_cols:
            return time_series_stats
        
        # 对每个日期列进行分析
        for date_col in date_cols:
            try:
                # 转换为日期类型
                df_time = df.copy()
                df_time[date_col] = pd.to_datetime(df_time[date_col])
                df_time = df_time.sort_values(date_col)
                
                # 获取数值列
                numeric_cols = df_time.select_dtypes(include=[np.number]).columns
                
                if len(numeric_cols) == 0:
                    continue
                
                # 计算第一个数值列的增长率
                value_col = numeric_cols[0]
                
                stats = {
                    "date_column": date_col,
                    "value_column": value_col,
                    "date_range": {
                        "start": df_time[date_col].min().isoformat() if pd.notna(df_time[date_col].min()) else None,
                        "end": df_time[date_col].max().isoformat() if pd.notna(df_time[date_col].max()) else None
                    }
                }
                
                # 计算环比增长率（相邻两期）
                if len(df_time) >= 2:
                    df_time["prev_value"] = df_time[value_col].shift(1)
                    df_time["mom_growth"] = (df_time[value_col] - df_time["prev_value"]) / df_time["prev_value"] * 100
                    
                    recent_mom = df_time["mom_growth"].dropna().iloc[-1] if len(df_time["mom_growth"].dropna()) > 0 else None
                    if recent_mom is not None:
                        stats["recent_mom_growth"] = float(recent_mom)
                
                # 计算整体增长率
                if len(df_time) >= 2:
                    first_value = df_time[value_col].iloc[0]
                    last_value = df_time[value_col].iloc[-1]
                    if first_value != 0:
                        overall_growth = (last_value - first_value) / first_value * 100
                        stats["overall_growth"] = float(overall_growth)
                
                time_series_stats[date_col] = stats
                
            except Exception as e:
                logger.warning(f"Failed to analyze time series for column {date_col}: {e}")
                continue
        
        return time_series_stats
    
    @staticmethod
    def _detect_anomalies(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        使用IQR（四分位距）方法检测异常值
        
        Returns:
            List: 异常点列表
        """
        anomalies = []
        
        # 获取数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:  # 至少需要4个数据点
                continue
            
            # 计算IQR
            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25
            
            # 定义异常值边界
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            
            # 检测异常值
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            if len(outliers) > 0:
                anomaly = {
                    "column": col,
                    "method": "IQR",
                    "count": len(outliers),
                    "bounds": {
                        "lower": float(lower_bound),
                        "upper": float(upper_bound)
                    },
                    "examples": []
                }
                
                # 记录几个异常值示例
                for idx in outliers.head(3).index:
                    anomaly["examples"].append({
                        "index": int(idx),
                        "value": float(df.loc[idx, col]),
                        "deviation": "高于上限" if df.loc[idx, col] > upper_bound else "低于下限"
                    })
                
                anomalies.append(anomaly)
        
        return anomalies
    
    @staticmethod
    def _analyze_categorical_columns(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        分析分类列的分布情况
        
        Returns:
            Dict: {列名: {统计信息}}
        """
        categorical_stats = {}
        
        # 获取非数值列
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        
        for col in categorical_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            value_counts = series.value_counts()
            
            stats = {
                "unique_count": int(series.nunique()),
                "most_common": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                "most_common_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "distribution": {}
            }
            
            # 只保留前10个最常见的值
            for value, count in value_counts.head(10).items():
                stats["distribution"][str(value)] = int(count)
            
            categorical_stats[col] = stats
        
        return categorical_stats
    
    @staticmethod
    def _generate_summary(stats: Dict[str, Any], df: pd.DataFrame) -> str:
        """
        生成文本摘要
        
        Returns:
            str: 摘要文本
        """
        summary_parts = []
        
        # 基本信息
        summary_parts.append(f"数据包含 {stats['total_rows']} 行，{stats['total_columns']} 列。")
        
        # 数值统计
        if stats["numeric_stats"]:
            numeric_summary = []
            for col, col_stats in stats["numeric_stats"].items():
                numeric_summary.append(
                    f"- **{col}**: 平均值 {col_stats['mean']:.2f}，"
                    f"中位数 {col_stats['median']:.2f}，"
                    f"范围 [{col_stats['min']:.2f}, {col_stats['max']:.2f}]"
                )
                
                # 波动性分析
                if col_stats['cv'] > 0.5:
                    numeric_summary.append(f"  （该指标波动较大，变异系数 {col_stats['cv']:.2f}）")
            
            if numeric_summary:
                summary_parts.append("\n数值指标统计：\n" + "\n".join(numeric_summary))
        
        # 时间序列分析
        if stats["time_series_stats"]:
            time_summary = []
            for date_col, ts_stats in stats["time_series_stats"].items():
                if "overall_growth" in ts_stats:
                    growth = ts_stats["overall_growth"]
                    direction = "增长" if growth > 0 else "下降"
                    time_summary.append(
                        f"- 从 {ts_stats['date_range']['start']} 到 {ts_stats['date_range']['end']}，"
                        f"整体{direction} {abs(growth):.2f}%"
                    )
                
                if "recent_mom_growth" in ts_stats:
                    mom = ts_stats["recent_mom_growth"]
                    direction = "增长" if mom > 0 else "下降"
                    time_summary.append(f"- 最近一期环比{direction} {abs(mom):.2f}%")
            
            if time_summary:
                summary_parts.append("\n时间趋势：\n" + "\n".join(time_summary))
        
        # 异常检测
        if stats["anomalies"]:
            anomaly_summary = []
            for anomaly in stats["anomalies"]:
                anomaly_summary.append(
                    f"- **{anomaly['column']}** 发现 {anomaly['count']} 个异常值"
                )
            
            if anomaly_summary:
                summary_parts.append("\n⚠️ 异常检测：\n" + "\n".join(anomaly_summary))
        
        return "\n".join(summary_parts)

