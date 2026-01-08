/**
 * 问题推荐和波动分析API接口
 */
import { http } from '@/utils/http'

// ============== 类型定义 ==============

export interface InputSuggestionRequest {
  dataset_id: number
  keyword: string
}

export interface SuggestionResponse {
  suggestions: string[]
}

export interface NextQuestionRequest {
  dataset_id: number
  question: string
  sql: string
  chart_type: string
  result_summary?: string
}

export interface FluctuationAnalysisRequest {
  dataset_id: number
  sql: string
  time_column: string
  value_column: string
  enable_drill_down?: boolean
}

export interface AnomalyPoint {
  index: number
  time: string
  value: number
  z_score: number
}

export interface StatisticsData {
  max_value: number
  min_value: number
  avg: number
  std_dev: number
  median: number
  coefficient_of_variation: number
  trend: string
  mom_growth: (number | null)[]
  anomaly_points: AnomalyPoint[]
  data_points: number
}

export interface DrillDownBreakdown {
  dimension_value: string
  value: number
  contribution_pct: number
}

export interface DrillDownData {
  dimension: string
  anomaly_time: string
  anomaly_value: number
  breakdown: DrillDownBreakdown[]
}

export interface FluctuationAnalysisResponse {
  stats: StatisticsData | null
  ai_insight: string
  drill_down: DrillDownData | null
}

// ============== API函数 ==============

/**
 * 输入联想：基于用户输入的关键词，AI生成相关问题
 */
export const getInputSuggestions = async (
  dataset_id: number,
  keyword: string
): Promise<SuggestionResponse> => {
  const response = await http.post('/chat/suggestions/input', {
    dataset_id,
    keyword
  })
  return response
}

/**
 * 猜你想问（结果后推荐）：基于当前查询结果，推荐后续问题
 */
export const getNextQuestions = async (
  data: NextQuestionRequest
): Promise<SuggestionResponse> => {
  const response = await http.post('/chat/suggestions/next', data)
  return response
}

/**
 * 获取数据集的热门问题
 */
export const getPopularQuestions = async (
  dataset_id: number
): Promise<SuggestionResponse> => {
  const response = await http.get(`/chat/suggestions/popular/${dataset_id}`)
  return response
}

/**
 * 波动归因分析：对时间序列数据进行三层分析
 */
export const analyzeFluctuation = async (
  data: FluctuationAnalysisRequest
): Promise<FluctuationAnalysisResponse> => {
  const response = await http.post('/chat/analyze/fluctuation', data)
  return response
}
