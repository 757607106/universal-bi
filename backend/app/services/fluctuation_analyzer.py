"""
波动归因分析服务

提供三层分析能力：
1. 统计分析：计算环比、同比、标准差、异常值检测
2. AI智能解读：基于统计结果生成业务语言的归因分析
3. 多维钻取：自动按其他维度拆解，找出波动贡献来源
"""
import pandas as pd
import numpy as np
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from app.core.logger import get_logger
from app.core.redis import get_redis_client
from app.core.security import decrypt_password
from app.models.metadata import Dataset
from app.services.vanna import VannaInstanceManager

logger = get_logger(__name__)


class FluctuationAnalyzer:
    """波动归因分析服务类"""
    
    # 缓存过期时间（秒）
    CACHE_TTL = 1800  # 30分钟
    
    # 异常检测阈值（标准差倍数）
    ANOMALY_THRESHOLD = 1.5
    
    @staticmethod
    def analyze(
        dataset_id: int,
        sql: str,
        time_column: str,
        value_column: str,
        db_session: Session,
        enable_drill_down: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整的波动归因分析
        
        Args:
            dataset_id: 数据集ID
            sql: 原始SQL查询
            time_column: 时间维度列名
            value_column: 指标值列名
            db_session: 数据库会话
            enable_drill_down: 是否启用多维钻取
            
        Returns:
            Dict: 包含统计分析、AI解读和多维钻取的完整结果
        """
        logger.info(f"Starting fluctuation analysis for dataset {dataset_id}")
        
        # 尝试从缓存获取
        cache_key = f"fluctuation:{dataset_id}:{hash(sql)}:{time_column}:{value_column}"
        redis_client = get_redis_client()
        
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Fluctuation analysis cache hit")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # 获取数据集和数据源
        dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.datasource:
            raise ValueError(f"Dataset {dataset_id} not found or no datasource")
        
        # 构建数据库连接
        datasource = dataset.datasource
        password = decrypt_password(datasource.password_encrypted)
        db_url = f"{datasource.type}+pymysql://{datasource.username}:{password}@{datasource.host}:{datasource.port}/{datasource.database_name}?charset=utf8mb4"
        engine = create_engine(db_url)
        
        # 执行SQL获取数据
        try:
            df = pd.read_sql(sql, engine)
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            raise ValueError(f"SQL执行失败: {str(e)}")
        
        if df.empty:
            return {
                "stats": None,
                "ai_insight": "数据为空，无法进行波动分析",
                "drill_down": None
            }
        
        # 验证列是否存在
        if time_column not in df.columns:
            raise ValueError(f"时间列 '{time_column}' 不存在")
        if value_column not in df.columns:
            raise ValueError(f"指标列 '{value_column}' 不存在")
        
        # Layer 1: 统计分析
        stats = FluctuationAnalyzer._compute_statistics(df, time_column, value_column)
        
        # Layer 2: AI智能解读
        ai_insight = FluctuationAnalyzer._generate_ai_insight(
            df=df,
            time_column=time_column,
            value_column=value_column,
            stats=stats,
            dataset_id=dataset_id
        )
        
        # Layer 3: 多维钻取
        drill_down = None
        if enable_drill_down and stats.get('anomaly_points'):
            try:
                drill_down = FluctuationAnalyzer._perform_drill_down(
                    df=df,
                    sql=sql,
                    time_column=time_column,
                    value_column=value_column,
                    anomaly_indices=stats['anomaly_points'],
                    engine=engine
                )
            except Exception as e:
                logger.error(f"Drill down analysis failed: {e}")
        
        result = {
            "stats": stats,
            "ai_insight": ai_insight,
            "drill_down": drill_down
        }
        
        # 缓存结果
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    FluctuationAnalyzer.CACHE_TTL,
                    json.dumps(result, ensure_ascii=False, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return result
    
    @staticmethod
    def _compute_statistics(
        df: pd.DataFrame,
        time_column: str,
        value_column: str
    ) -> Dict[str, Any]:
        """
        计算统计指标
        
        Args:
            df: 数据DataFrame
            time_column: 时间列名
            value_column: 指标列名
            
        Returns:
            Dict: 统计指标
        """
        # 确保数据按时间排序
        df = df.sort_values(by=time_column).reset_index(drop=True)
        
        values = df[value_column].astype(float)
        
        # 基础统计
        max_value = float(values.max())
        min_value = float(values.min())
        avg = float(values.mean())
        std_dev = float(values.std())
        median = float(values.median())
        
        # 环比增长率 (Month-over-Month)
        mom_growth = []
        if len(values) > 1:
            for i in range(1, len(values)):
                if values.iloc[i-1] != 0:
                    growth = (values.iloc[i] - values.iloc[i-1]) / values.iloc[i-1]
                    mom_growth.append(float(growth))
                else:
                    mom_growth.append(None)
        
        # 异常点检测（基于标准差）
        anomaly_points = []
        if std_dev > 0:
            z_scores = np.abs((values - avg) / std_dev)
            anomaly_indices = np.where(z_scores > FluctuationAnalyzer.ANOMALY_THRESHOLD)[0]
            anomaly_points = [
                {
                    "index": int(idx),
                    "time": str(df.iloc[idx][time_column]),
                    "value": float(df.iloc[idx][value_column]),
                    "z_score": float(z_scores.iloc[idx])
                }
                for idx in anomaly_indices
            ]
        
        # 趋势判断（简单线性回归）
        trend = "平稳"
        if len(values) > 2:
            x = np.arange(len(values))
            coefficients = np.polyfit(x, values, 1)
            slope = coefficients[0]
            if slope > avg * 0.05:  # 上升超过5%
                trend = "上升"
            elif slope < -avg * 0.05:  # 下降超过5%
                trend = "下降"
        
        # 波动幅度（变异系数）
        cv = (std_dev / avg * 100) if avg != 0 else 0
        
        return {
            "max_value": max_value,
            "min_value": min_value,
            "avg": avg,
            "std_dev": std_dev,
            "median": median,
            "coefficient_of_variation": float(cv),
            "trend": trend,
            "mom_growth": mom_growth,
            "anomaly_points": anomaly_points,
            "data_points": len(values)
        }
    
    @staticmethod
    def _generate_ai_insight(
        df: pd.DataFrame,
        time_column: str,
        value_column: str,
        stats: Dict[str, Any],
        dataset_id: int
    ) -> str:
        """
        使用AI生成波动归因分析
        
        Args:
            df: 数据DataFrame
            time_column: 时间列名
            value_column: 指标列名
            stats: 统计指标
            dataset_id: 数据集ID
            
        Returns:
            str: AI生成的归因分析文本
        """
        # 构建数据摘要
        data_summary = []
        df_sorted = df.sort_values(by=time_column)
        for idx, row in df_sorted.head(10).iterrows():
            data_summary.append(f"{row[time_column]}: {row[value_column]}")
        
        if len(df) > 10:
            data_summary.append(f"... (共{len(df)}个数据点)")
        
        data_summary_str = "\n".join(data_summary)
        
        # 构建Prompt
        system_prompt = """你是一个数据分析师，擅长数据波动归因分析。
基于提供的时间序列数据和统计指标，生成业务语言的归因分析报告。

要求：
1. 用业务语言描述，避免专业术语
2. 重点指出异常波动及其可能原因
3. 提供actionable的建议
4. 控制在150字以内
5. 直接输出分析内容，不要前缀如"分析："
"""
        
        user_prompt = f"""数据序列：
{data_summary_str}

统计指标：
- 平均值: {stats['avg']:.2f}
- 标准差: {stats['std_dev']:.2f}
- 最大值: {stats['max_value']:.2f}
- 最小值: {stats['min_value']:.2f}
- 趋势: {stats['trend']}
- 变异系数: {stats['coefficient_of_variation']:.1f}%
- 异常点数量: {len(stats['anomaly_points'])}

请分析数据波动情况和可能的原因："""
        
        try:
            vn = VannaInstanceManager.get_instance(dataset_id)
            response = vn.submit_prompt(
                prompt=user_prompt,
                system_message=system_prompt
            )
            
            # 清理响应（去除可能的前缀）
            insight = response.strip()
            insight = re.sub(r'^(分析[:：]|波动分析[:：]|归因分析[:：])\s*', '', insight)
            
            return insight
            
        except Exception as e:
            logger.error(f"AI insight generation failed: {e}")
            return FluctuationAnalyzer._generate_fallback_insight(stats)
    
    @staticmethod
    def _generate_fallback_insight(stats: Dict[str, Any]) -> str:
        """
        生成兜底的分析文本
        
        Args:
            stats: 统计指标
            
        Returns:
            str: 兜底分析文本
        """
        trend_desc = {
            "上升": "呈现上升趋势",
            "下降": "呈现下降趋势",
            "平稳": "整体较为平稳"
        }
        
        insight_parts = []
        
        # 趋势描述
        insight_parts.append(f"数据{trend_desc.get(stats['trend'], '波动较大')}")
        
        # 波动描述
        if stats['coefficient_of_variation'] > 30:
            insight_parts.append(f"波动幅度较大（变异系数{stats['coefficient_of_variation']:.1f}%）")
        elif stats['coefficient_of_variation'] < 10:
            insight_parts.append("波动幅度较小，数据较为稳定")
        
        # 异常点描述
        if len(stats['anomaly_points']) > 0:
            anomaly_times = [ap['time'] for ap in stats['anomaly_points'][:3]]
            insight_parts.append(f"在{', '.join(anomaly_times)}等时间点出现异常波动")
        
        # 极值描述
        value_range = stats['max_value'] - stats['min_value']
        if value_range > stats['avg'] * 0.5:
            insight_parts.append(f"最大值({stats['max_value']:.0f})与最小值({stats['min_value']:.0f})差距较大")
        
        return "，".join(insight_parts) + "。建议进一步分析异常时间点的具体原因。"
    
    @staticmethod
    def _perform_drill_down(
        df: pd.DataFrame,
        sql: str,
        time_column: str,
        value_column: str,
        anomaly_indices: List[Dict[str, Any]],
        engine: Any
    ) -> Optional[Dict[str, Any]]:
        """
        执行多维钻取分析
        
        Args:
            df: 原始数据DataFrame
            sql: 原始SQL
            time_column: 时间列名
            value_column: 指标列名
            anomaly_indices: 异常点列表
            engine: 数据库引擎
            
        Returns:
            Dict: 钻取分析结果，如果无法钻取则返回None
        """
        if not anomaly_indices:
            return None
        
        # 尝试识别SQL中的GROUP BY维度
        dimensions = FluctuationAnalyzer._extract_group_by_dimensions(sql, time_column)
        
        if not dimensions:
            logger.info("No additional dimensions found for drill-down")
            return None
        
        # 选择第一个异常点进行钻取
        anomaly = anomaly_indices[0]
        anomaly_time = anomaly['time']
        
        logger.info(f"Drilling down on anomaly at {anomaly_time}, dimension: {dimensions[0]}")
        
        # 构建钻取SQL
        drill_sql = FluctuationAnalyzer._build_drill_down_sql(
            sql=sql,
            time_column=time_column,
            value_column=value_column,
            anomaly_time=anomaly_time,
            dimension=dimensions[0]
        )
        
        if not drill_sql:
            return None
        
        try:
            # 执行钻取查询
            drill_df = pd.read_sql(drill_sql, engine)
            
            if drill_df.empty:
                return None
            
            # 计算各维度的贡献
            total = drill_df[value_column].sum()
            breakdown = []
            
            for _, row in drill_df.iterrows():
                value = float(row[value_column])
                contribution = (value / total * 100) if total != 0 else 0
                breakdown.append({
                    "dimension_value": str(row[dimensions[0]]),
                    "value": value,
                    "contribution_pct": float(contribution)
                })
            
            # 按贡献度排序
            breakdown.sort(key=lambda x: x['contribution_pct'], reverse=True)
            
            return {
                "dimension": dimensions[0],
                "anomaly_time": anomaly_time,
                "anomaly_value": anomaly['value'],
                "breakdown": breakdown[:10]  # 最多返回前10个
            }
            
        except Exception as e:
            logger.error(f"Drill-down query failed: {e}")
            return None
    
    @staticmethod
    def _extract_group_by_dimensions(sql: str, exclude_column: str) -> List[str]:
        """
        从SQL中提取GROUP BY的维度列
        
        Args:
            sql: SQL查询
            exclude_column: 要排除的列（通常是时间列）
            
        Returns:
            List[str]: 维度列名列表
        """
        # 提取GROUP BY子句
        group_by_match = re.search(
            r'GROUP\s+BY\s+([^HAVING|ORDER|LIMIT|;]+)',
            sql,
            re.IGNORECASE
        )
        
        if not group_by_match:
            return []
        
        group_by_clause = group_by_match.group(1)
        
        # 分割列名
        columns = [col.strip() for col in group_by_clause.split(',')]
        
        # 清理列名（去除表别名、函数调用等）
        cleaned_columns = []
        for col in columns:
            # 去除表别名 (如 t.column_name -> column_name)
            if '.' in col:
                col = col.split('.')[-1]
            
            # 去除函数调用（如 DATE(column) -> column）
            func_match = re.search(r'\w+\((.+?)\)', col)
            if func_match:
                col = func_match.group(1).strip()
            
            col = col.strip('`"\'')
            
            if col and col.lower() != exclude_column.lower():
                cleaned_columns.append(col)
        
        return cleaned_columns
    
    @staticmethod
    def _build_drill_down_sql(
        sql: str,
        time_column: str,
        value_column: str,
        anomaly_time: str,
        dimension: str
    ) -> Optional[str]:
        """
        构建钻取SQL
        
        Args:
            sql: 原始SQL
            time_column: 时间列名
            value_column: 指标列名
            anomaly_time: 异常时间点
            dimension: 钻取维度
            
        Returns:
            str: 钻取SQL，如果无法构建则返回None
        """
        try:
            # 简化策略：在原SQL基础上添加WHERE条件和修改GROUP BY
            # 这里采用子查询方式更安全
            drill_sql = f"""
SELECT {dimension}, SUM({value_column}) as {value_column}
FROM ({sql}) as base_query
WHERE {time_column} = '{anomaly_time}'
GROUP BY {dimension}
ORDER BY {value_column} DESC
LIMIT 20
"""
            return drill_sql.strip()
            
        except Exception as e:
            logger.error(f"Failed to build drill-down SQL: {e}")
            return None
