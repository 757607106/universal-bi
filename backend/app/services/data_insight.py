"""
数据解读服务 - 自动分析数据特征并生成解读
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from openai import OpenAI as OpenAIClient

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class DataInsightAnalyzer:
    """数据解读分析器 - 自动分析数据特征并生成 AI 解读"""
    
    @classmethod
    async def analyze_data(
        cls,
        df: pd.DataFrame,
        question: str,
        dataset_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        分析数据并生成解读
        
        Args:
            df: 查询结果 DataFrame
            question: 用户问题
            dataset_id: 数据集 ID
            
        Returns:
            Dict: {
                "summary": "数据解读文本",
                "key_findings": ["发现1", "发现2"],
                "statistics": {...},
                "quality_score": 95
            }
        """
        if df is None or df.empty:
            return None
        
        try:
            # 对于大数据集，仅分析前 100 行样本
            sample_df = df.head(100) if len(df) > 100 else df
            
            # 1. 描述性统计
            statistics = cls._compute_statistics(sample_df, df)
            
            # 2. 数据分布分析
            distribution = cls._analyze_distribution(sample_df)
            
            # 3. 数据质量分析
            quality = cls._analyze_quality(sample_df)
            
            # 4. 趋势识别
            trend = cls._identify_trend(sample_df)
            
            # 5. 生成关键发现
            key_findings = cls._extract_key_findings(
                statistics, distribution, quality, trend
            )
            
            # 6. 使用 LLM 生成自然语言解读
            summary = await cls._generate_summary_with_llm(
                question=question,
                statistics=statistics,
                distribution=distribution,
                quality=quality,
                trend=trend,
                key_findings=key_findings
            )
            
            logger.info(
                "Data insight analysis completed",
                dataset_id=dataset_id,
                row_count=len(df),
                column_count=len(df.columns),
                quality_score=quality.get('quality_score', 0)
            )
            
            return {
                "summary": summary,
                "key_findings": key_findings,
                "statistics": {
                    **statistics,
                    "distribution": distribution,
                    "trend": trend
                },
                "quality_score": quality.get('quality_score')
            }
            
        except Exception as e:
            logger.error(
                "Data insight analysis failed",
                error=str(e),
                dataset_id=dataset_id,
                exc_info=True
            )
            return None
    
    @classmethod
    def _compute_statistics(cls, sample_df: pd.DataFrame, full_df: pd.DataFrame) -> Dict[str, Any]:
        """计算描述性统计"""
        stats = {
            "total_rows": len(full_df),
            "total_columns": len(full_df.columns),
            "column_names": full_df.columns.tolist(),
            "numeric_columns": [],
            "categorical_columns": [],
            "datetime_columns": []
        }
        
        for col in sample_df.columns:
            if pd.api.types.is_numeric_dtype(sample_df[col]):
                stats["numeric_columns"].append({
                    "name": col,
                    "mean": float(sample_df[col].mean()) if not sample_df[col].isna().all() else None,
                    "median": float(sample_df[col].median()) if not sample_df[col].isna().all() else None,
                    "min": float(sample_df[col].min()) if not sample_df[col].isna().all() else None,
                    "max": float(sample_df[col].max()) if not sample_df[col].isna().all() else None,
                    "std": float(sample_df[col].std()) if not sample_df[col].isna().all() else None
                })
            elif pd.api.types.is_datetime64_any_dtype(sample_df[col]):
                stats["datetime_columns"].append({
                    "name": col,
                    "min": str(sample_df[col].min()),
                    "max": str(sample_df[col].max())
                })
            else:
                unique_count = sample_df[col].nunique()
                stats["categorical_columns"].append({
                    "name": col,
                    "unique_count": unique_count
                })
        
        return stats
    
    @classmethod
    def _analyze_distribution(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据分布"""
        distribution = {
            "top_values": {},
            "bottom_values": {}
        }
        
        # 对数值列分析 TOP/BOTTOM
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols[:3]:  # 最多分析 3 个数值列
            try:
                if not df[col].isna().all():
                    top_5 = df.nlargest(5, col)[[col]].to_dict('records')
                    bottom_5 = df.nsmallest(5, col)[[col]].to_dict('records')
                    
                    distribution["top_values"][col] = [
                        float(item[col]) for item in top_5 if pd.notna(item[col])
                    ]
                    distribution["bottom_values"][col] = [
                        float(item[col]) for item in bottom_5 if pd.notna(item[col])
                    ]
            except Exception as e:
                logger.debug(f"Failed to analyze distribution for column {col}: {e}")
                continue
        
        # 对分类列分析值分布
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        for col in categorical_cols[:2]:  # 最多分析 2 个分类列
            try:
                value_counts = df[col].value_counts().head(5)
                distribution[f"{col}_distribution"] = value_counts.to_dict()
            except Exception as e:
                logger.debug(f"Failed to analyze categorical distribution for {col}: {e}")
                continue
        
        return distribution
    
    @classmethod
    def _analyze_quality(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据质量"""
        quality = {
            "null_percentages": {},
            "outlier_columns": [],
            "quality_score": 100
        }
        
        # 计算空值比例
        for col in df.columns:
            null_pct = (df[col].isna().sum() / len(df)) * 100
            if null_pct > 0:
                quality["null_percentages"][col] = round(null_pct, 2)
                quality["quality_score"] -= min(null_pct / 10, 5)  # 每 10% 空值扣 1 分，最多扣 5 分
        
        # 检测异常值（基于 IQR 方法）
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            try:
                if not df[col].isna().all():
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    outliers = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
                    outlier_pct = (outliers / len(df)) * 100
                    
                    if outlier_pct > 5:  # 超过 5% 认为有异常值
                        quality["outlier_columns"].append({
                            "column": col,
                            "outlier_percentage": round(outlier_pct, 2)
                        })
                        quality["quality_score"] -= min(outlier_pct / 5, 3)  # 扣分
            except Exception as e:
                logger.debug(f"Failed to detect outliers for column {col}: {e}")
                continue
        
        quality["quality_score"] = max(0, min(100, round(quality["quality_score"])))
        
        return quality
    
    @classmethod
    def _identify_trend(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """识别趋势（仅对时间序列数据）"""
        # 查找日期列
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        
        if len(datetime_cols) == 0:
            # 尝试解析 object 类型的日期列
            for col in df.select_dtypes(include=['object']).columns:
                try:
                    pd.to_datetime(df[col].iloc[0])
                    datetime_cols = [col]
                    break
                except:
                    continue
        
        if len(datetime_cols) == 0:
            return None
        
        # 查找数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return None
        
        try:
            time_col = datetime_cols[0]
            value_col = numeric_cols[0]
            
            # 按时间排序
            sorted_df = df.sort_values(time_col)
            values = sorted_df[value_col].dropna()
            
            if len(values) < 3:
                return None
            
            # 简单趋势判断
            first_half_mean = values.iloc[:len(values)//2].mean()
            second_half_mean = values.iloc[len(values)//2:].mean()
            
            if second_half_mean > first_half_mean * 1.1:
                trend_direction = "上升"
            elif second_half_mean < first_half_mean * 0.9:
                trend_direction = "下降"
            else:
                trend_direction = "平稳"
            
            change_rate = ((second_half_mean - first_half_mean) / first_half_mean * 100) if first_half_mean != 0 else 0
            
            return {
                "has_trend": True,
                "time_column": time_col,
                "value_column": value_col,
                "trend_direction": trend_direction,
                "change_rate": round(change_rate, 2)
            }
            
        except Exception as e:
            logger.debug(f"Failed to identify trend: {e}")
            return None
    
    @classmethod
    def _extract_key_findings(
        cls,
        statistics: Dict,
        distribution: Dict,
        quality: Dict,
        trend: Optional[Dict]
    ) -> List[str]:
        """提取关键发现"""
        findings = []
        
        # 1. 数据规模
        total_rows = statistics.get("total_rows", 0)
        total_cols = statistics.get("total_columns", 0)
        findings.append(f"数据集包含 {total_rows} 行数据和 {total_cols} 个字段")
        
        # 2. 数据质量
        quality_score = quality.get("quality_score", 100)
        if quality_score >= 90:
            findings.append(f"数据质量优秀（{quality_score}分）")
        elif quality_score >= 70:
            findings.append(f"数据质量良好（{quality_score}分），存在少量空值或异常")
        else:
            findings.append(f"数据质量需要关注（{quality_score}分），存在较多空值或异常")
        
        # 3. 趋势
        if trend and trend.get("has_trend"):
            direction = trend.get("trend_direction")
            change_rate = trend.get("change_rate", 0)
            findings.append(f"数据呈现{direction}趋势，变化率约 {change_rate:.1f}%")
        
        # 4. 分布特征
        numeric_cols = statistics.get("numeric_columns", [])
        if numeric_cols:
            col = numeric_cols[0]
            name = col.get("name")
            mean_val = col.get("mean")
            if mean_val:
                findings.append(f"{name} 的平均值为 {mean_val:.2f}")
        
        return findings[:5]  # 最多返回 5 个关键发现
    
    @classmethod
    async def _generate_summary_with_llm(
        cls,
        question: str,
        statistics: Dict,
        distribution: Dict,
        quality: Dict,
        trend: Optional[Dict],
        key_findings: List[str]
    ) -> str:
        """使用 LLM 生成自然语言解读"""
        try:
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 构建上下文
            context = f"""用户问题：{question}

数据统计信息：
- 总行数：{statistics.get('total_rows')}
- 总列数：{statistics.get('total_columns')}
- 数值列：{len(statistics.get('numeric_columns', []))} 个
- 分类列：{len(statistics.get('categorical_columns', []))} 个

关键发现：
{chr(10).join(['- ' + f for f in key_findings])}

数据质量评分：{quality.get('quality_score')} 分
"""

            if trend:
                context += f"\n趋势分析：\n- 趋势方向：{trend.get('trend_direction')}\n- 变化率：{trend.get('change_rate')}%"
            
            system_prompt = """你是一个专业的数据分析师，擅长解读数据并生成简洁、易懂的分析报告。

任务：
- 基于提供的数据统计信息，生成 100-150 字的数据解读
- 重点突出数据特征、趋势和关键洞察
- 使用通俗易懂的语言，避免过多技术术语
- 如果有明显的趋势或异常，重点说明

输出要求：
- 段落格式，不要使用列表
- 简洁明了，直击要点
- 使用中文
"""

            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content.strip()
            
            logger.debug(
                "Data insight summary generated",
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary with LLM: {e}", exc_info=True)
            # 降级：返回基于模板的摘要
            return cls._generate_fallback_summary(key_findings, quality)
    
    @classmethod
    def _generate_fallback_summary(cls, key_findings: List[str], quality: Dict) -> str:
        """生成降级摘要（不使用 LLM）"""
        quality_score = quality.get("quality_score", 100)
        
        summary = "数据分析摘要：" + "；".join(key_findings[:3])
        
        if quality_score < 70:
            summary += "。建议关注数据质量问题，优化数据采集流程。"
        
        return summary
