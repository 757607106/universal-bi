"""
问题推荐和波动分析相关的Pydantic Schema定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class InputSuggestionRequest(BaseModel):
    """输入联想请求"""
    dataset_id: int = Field(..., description="数据集ID")
    keyword: str = Field(..., min_length=2, max_length=50, description="用户输入的关键词")


class SuggestionResponse(BaseModel):
    """问题推荐响应"""
    suggestions: List[str] = Field(..., description="推荐的问题列表")


class NextQuestionRequest(BaseModel):
    """猜你想问请求（结果后推荐）"""
    dataset_id: int = Field(..., description="数据集ID")
    question: str = Field(..., description="当前用户问题")
    sql: str = Field(..., description="当前生成的SQL")
    chart_type: str = Field(..., description="图表类型")
    result_summary: Optional[str] = Field(None, description="结果摘要（可选）")


class FluctuationAnalysisRequest(BaseModel):
    """波动归因分析请求"""
    dataset_id: int = Field(..., description="数据集ID")
    sql: str = Field(..., description="原始SQL查询")
    time_column: str = Field(..., description="时间维度列名")
    value_column: str = Field(..., description="指标值列名")
    enable_drill_down: bool = Field(True, description="是否启用多维钻取")


class StatisticsData(BaseModel):
    """统计数据"""
    max_value: float
    min_value: float
    avg: float
    std_dev: float
    median: float
    coefficient_of_variation: float
    trend: str  # "上升", "下降", "平稳"
    mom_growth: List[Optional[float]]  # 环比增长率
    anomaly_points: List[Dict[str, Any]]  # 异常点列表
    data_points: int


class DrillDownBreakdown(BaseModel):
    """钻取维度拆解"""
    dimension_value: str
    value: float
    contribution_pct: float


class DrillDownData(BaseModel):
    """多维钻取数据"""
    dimension: str
    anomaly_time: str
    anomaly_value: float
    breakdown: List[DrillDownBreakdown]


class FluctuationAnalysisResponse(BaseModel):
    """波动归因分析响应"""
    stats: Optional[StatisticsData] = Field(None, description="统计分析结果")
    ai_insight: str = Field(..., description="AI生成的归因分析")
    drill_down: Optional[DrillDownData] = Field(None, description="多维钻取结果")
