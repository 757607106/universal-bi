"""
波动归因服务 - 智能分析数据波动并推理原因
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from openai import OpenAI as OpenAIClient

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class FluctuationAnalyzer:
    """波动归因分析器 - 检测数据波动并进行归因分析"""
    
    # 波动阈值配置
    SIGNIFICANT_CHANGE_THRESHOLD = 0.15  # 15% 变化认为是显著波动
    OUTLIER_THRESHOLD = 2.5  # 2.5 倍标准差认为是异常值
    
    @classmethod
    async def analyze_fluctuation(
        cls,
        df: pd.DataFrame,
        question: str,
        dataset_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        分析数据波动并进行归因
        
        Args:
            df: 查询结果 DataFrame
            question: 用户问题
            dataset_id: 数据集 ID
            
        Returns:
            Dict: {
                "has_fluctuation": bool,
                "fluctuation_points": [...],
                "attribution": {
                    "main_factors": [...],
                    "detailed_analysis": "..."
                },
                "chart_recommendation": "waterfall"
            }
        """
        if df is None or df.empty or len(df) < 3:
            return None
        
        try:
            # 对于大数据集，仅分析前 100 行
            sample_df = df.head(100) if len(df) > 100 else df
            
            # 1. 检测波动点
            fluctuations = cls._detect_fluctuations(sample_df)
            
            if not fluctuations:
                logger.info(
                    "No significant fluctuation detected",
                    dataset_id=dataset_id,
                    row_count=len(df)
                )
                return {
                    "has_fluctuation": False,
                    "fluctuation_points": [],
                    "attribution": None,
                    "chart_recommendation": None
                }
            
            # 2. 进行归因分析
            attribution = await cls._perform_attribution(
                df=sample_df,
                fluctuations=fluctuations,
                question=question
            )
            
            # 3. 推荐图表类型
            chart_recommendation = cls._recommend_chart(fluctuations, sample_df)
            
            logger.info(
                "Fluctuation analysis completed",
                dataset_id=dataset_id,
                fluctuation_count=len(fluctuations),
                has_attribution=attribution is not None
            )
            
            return {
                "has_fluctuation": True,
                "fluctuation_points": fluctuations,
                "attribution": attribution,
                "chart_recommendation": chart_recommendation
            }
            
        except Exception as e:
            logger.error(
                "Fluctuation analysis failed",
                error=str(e),
                dataset_id=dataset_id,
                exc_info=True
            )
            return None
    
    @classmethod
    def _detect_fluctuations(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """检测数据波动点"""
        fluctuations = []
        
        # 查找数值列
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return fluctuations
        
        # 对每个数值列进行波动检测
        for col in numeric_cols:
            try:
                values = df[col].dropna()
                
                if len(values) < 3:
                    continue
                
                # 方法 1: 基于标准差的异常值检测
                mean_val = values.mean()
                std_val = values.std()
                
                if std_val == 0:
                    continue
                
                outlier_mask = np.abs((values - mean_val) / std_val) > cls.OUTLIER_THRESHOLD
                outlier_indices = values[outlier_mask].index.tolist()
                
                if outlier_indices:
                    for idx in outlier_indices[:3]:  # 最多记录 3 个异常点
                        fluctuations.append({
                            "type": "outlier",
                            "column": col,
                            "index": int(idx),
                            "value": float(df.loc[idx, col]),
                            "mean": float(mean_val),
                            "std": float(std_val),
                            "deviation": float(abs(df.loc[idx, col] - mean_val) / std_val)
                        })
                
                # 方法 2: 环比变化检测（如果有时间序列）
                datetime_cols = df.select_dtypes(include=['datetime64']).columns
                
                if len(datetime_cols) > 0:
                    time_col = datetime_cols[0]
                    sorted_df = df.sort_values(time_col)
                    sorted_values = sorted_df[col].dropna()
                    
                    if len(sorted_values) >= 2:
                        # 计算环比变化率
                        pct_changes = sorted_values.pct_change().dropna()
                        
                        significant_changes = pct_changes[
                            np.abs(pct_changes) > cls.SIGNIFICANT_CHANGE_THRESHOLD
                        ]
                        
                        for idx in significant_changes.index[:3]:  # 最多记录 3 个显著变化
                            current_val = sorted_df.loc[idx, col]
                            prev_idx = sorted_df.index[sorted_df.index.get_loc(idx) - 1]
                            prev_val = sorted_df.loc[prev_idx, col]
                            change_rate = pct_changes.loc[idx]
                            
                            fluctuations.append({
                                "type": "significant_change",
                                "column": col,
                                "time_column": time_col,
                                "index": int(idx),
                                "current_value": float(current_val),
                                "previous_value": float(prev_val),
                                "change_rate": float(change_rate * 100),
                                "direction": "增长" if change_rate > 0 else "下降"
                            })
                
            except Exception as e:
                logger.debug(f"Failed to detect fluctuations for column {col}: {e}")
                continue
        
        # 按波动程度排序
        fluctuations.sort(
            key=lambda x: abs(x.get('deviation', 0)) + abs(x.get('change_rate', 0) / 100),
            reverse=True
        )
        
        return fluctuations[:5]  # 最多返回 5 个波动点
    
    @classmethod
    async def _perform_attribution(
        cls,
        df: pd.DataFrame,
        fluctuations: List[Dict],
        question: str
    ) -> Optional[Dict[str, Any]]:
        """执行归因分析（使用 LLM 推理）"""
        if not fluctuations:
            return None
        
        try:
            # 准备数据上下文
            context = cls._prepare_attribution_context(df, fluctuations, question)
            
            # 调用 LLM 进行归因分析
            attribution = await cls._generate_attribution_with_llm(context)
            
            return attribution
            
        except Exception as e:
            logger.error(f"Attribution analysis failed: {e}", exc_info=True)
            return cls._generate_fallback_attribution(fluctuations)
    
    @classmethod
    def _prepare_attribution_context(
        cls,
        df: pd.DataFrame,
        fluctuations: List[Dict],
        question: str
    ) -> str:
        """准备归因分析的上下文信息"""
        context = f"用户问题：{question}\n\n"
        context += f"数据维度：{', '.join(df.columns.tolist())}\n"
        context += f"数据规模：{len(df)} 行\n\n"
        context += "检测到的波动：\n"
        
        for i, fluct in enumerate(fluctuations, 1):
            if fluct['type'] == 'outlier':
                context += f"{i}. {fluct['column']} 存在异常值：{fluct['value']:.2f}（偏离均值 {fluct['deviation']:.2f} 倍标准差）\n"
            elif fluct['type'] == 'significant_change':
                context += f"{i}. {fluct['column']} 出现显著{fluct['direction']}：变化率 {fluct['change_rate']:.1f}%\n"
        
        # 添加分类维度信息（用于多维度归因）
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        if len(categorical_cols) > 0:
            context += "\n可用于归因的维度：\n"
            for col in categorical_cols[:3]:
                unique_vals = df[col].nunique()
                context += f"- {col}（{unique_vals} 个不同值）\n"
        
        return context
    
    @classmethod
    async def _generate_attribution_with_llm(cls, context: str) -> Dict[str, Any]:
        """使用 LLM 生成归因分析"""
        try:
            client = OpenAIClient(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            system_prompt = """你是一个专业的数据分析师，擅长波动归因分析。

任务：
- 基于检测到的数据波动和可用维度，推理可能的波动原因
- 提供 2-3 个主要归因因素
- 给出 100-150 字的详细分析

输出要求（JSON 格式）：
{
  "main_factors": ["因素1", "因素2", "因素3"],
  "detailed_analysis": "详细的归因分析文本，解释波动原因和影响"
}

注意：
- 基于数据特征进行合理推测，不要过度猜测
- 如果有明显的时间、地区、类别维度，重点分析
- 使用简洁、专业的语言
"""

            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.4,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            # 解析 JSON 响应
            import json
            attribution = json.loads(content)
            
            logger.debug("Attribution generated with LLM")
            
            return attribution
            
        except Exception as e:
            logger.error(f"Failed to generate attribution with LLM: {e}", exc_info=True)
            raise
    
    @classmethod
    def _generate_fallback_attribution(cls, fluctuations: List[Dict]) -> Dict[str, Any]:
        """生成降级归因（不使用 LLM）"""
        main_factors = []
        
        # 基于波动类型生成简单归因
        has_outlier = any(f['type'] == 'outlier' for f in fluctuations)
        has_change = any(f['type'] == 'significant_change' for f in fluctuations)
        
        if has_outlier:
            main_factors.append("数据存在异常值，可能由数据录入错误或特殊事件引起")
        
        if has_change:
            change_fluct = next((f for f in fluctuations if f['type'] == 'significant_change'), None)
            if change_fluct:
                direction = change_fluct.get('direction', '变化')
                main_factors.append(f"数据呈现{direction}趋势，可能受业务变化或季节因素影响")
        
        if not main_factors:
            main_factors.append("数据波动可能由多种因素综合影响")
        
        detailed_analysis = "检测到数据存在显著波动。" + "；".join(main_factors) + "。建议进一步细分维度进行深入分析。"
        
        return {
            "main_factors": main_factors[:3],
            "detailed_analysis": detailed_analysis
        }
    
    @classmethod
    def _recommend_chart(cls, fluctuations: List[Dict], df: pd.DataFrame) -> str:
        """推荐适合展示波动归因的图表类型"""
        # 如果有时间序列变化，推荐折线图
        has_time_change = any(
            f['type'] == 'significant_change' and 'time_column' in f
            for f in fluctuations
        )
        
        if has_time_change:
            return "line"  # 折线图适合展示趋势变化
        
        # 如果有分类维度，推荐柱状图或瀑布图
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        if len(categorical_cols) > 0:
            return "bar"  # 柱状图适合对比不同类别
        
        # 默认推荐柱状图
        return "bar"
