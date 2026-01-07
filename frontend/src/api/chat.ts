import { http } from "@/utils/http"

export interface ChatResponse {
  answer_text?: string  // For clarification requests
  sql: string | null
  columns?: string[] | null  // 支持直接返回 columns
  rows?: any[] | null  // 支持直接返回 rows
  data: {
    columns: string[] | null
    rows: any[] | null
  } | null
  chart_type: string
  steps?: string[]  // Execution steps tracking
  from_cache?: boolean  // Whether result is from cache (deprecated, use is_cached)
  is_cached?: boolean  // Whether result is from cache
  insight?: string  // Business insight from analyst agent
}

export interface SummaryRequest {
  dataset_id: number
  question: string
  sql: string
  columns: string[]
  rows: any[]
}

export interface SummaryResponse {
  summary: string
}

export interface FeedbackRequest {
  dataset_id: number
  question: string
  sql: string
  rating: number  // 1 for like, -1 for dislike
}

export interface FeedbackResponse {
  success: boolean
  message: string
}

export const sendChat = async (data: { dataset_id: number, question: string, use_cache?: boolean }) => {
  const responseData = await http.post<any, { dataset_id: number, question: string, use_cache?: boolean }>('/chat/', data)
  // 直接返回后端数据，保留原始结构
  return {
    answer_text: responseData.answer_text || responseData.summary,
    sql: responseData.sql,
    columns: responseData.columns,  // 直接传递
    rows: responseData.rows,  // 直接传递
    data: null,  // 不再包装
    chart_type: responseData.chart_type,
    steps: responseData.steps || [],
    from_cache: responseData.from_cache || false,  // 兼容旧字段
    is_cached: responseData.is_cached || false,  // 新字段
    insight: responseData.insight  // 业务分析
  } as ChatResponse
}

export const generateSummary = async (data: SummaryRequest): Promise<SummaryResponse> => {
  return await http.post<SummaryResponse, SummaryRequest>('/chat/summary', data)
}

export const submitFeedback = async (data: FeedbackRequest): Promise<FeedbackResponse> => {
  return await http.post<FeedbackResponse, FeedbackRequest>('/chat/feedback', data)
}
