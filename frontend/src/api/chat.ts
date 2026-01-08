import { http } from "@/utils/http"

export interface DataInterpretation {
  summary: string
  key_findings: string[]
  statistics: Record<string, any>
  quality_score?: number
}

export interface FluctuationAnalysis {
  has_fluctuation: boolean
  fluctuation_points?: any[]
  attribution?: {
    main_factors?: string[]
    detailed_analysis?: string
  }
  chart_recommendation?: string
}

export interface ChatResponse {
  answer_text?: string  // For clarification requests
  sql: string | null
  columns?: string[] | null
  rows?: any[] | null
  chart_type: string
  alternative_charts?: string[]  // 备选图表类型
  steps?: string[]  // Execution steps tracking
  is_cached?: boolean  // Whether result is from cache
  insight?: string  // Business insight from analyst agent
  data_interpretation?: DataInterpretation  // 数据解读
  fluctuation_analysis?: FluctuationAnalysis  // 波动归因
  followup_questions?: string[]  // 后续推荐问题
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

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export const sendChat = async (data: {
  dataset_id: number,
  question: string,
  use_cache?: boolean,
  conversation_history?: ConversationMessage[],
  data_table_id?: number,
  session_id?: number
}) => {
  const responseData = await http.post<any, {
    dataset_id: number,
    question: string,
    use_cache?: boolean,
    conversation_history?: ConversationMessage[],
    data_table_id?: number,
    session_id?: number
  }>('/chat/', data)
  // 直接返回后端数据，保留原始结构
  return {
    answer_text: responseData.answer_text || responseData.summary,
    sql: responseData.sql,
    columns: responseData.columns,
    rows: responseData.rows,
    chart_type: responseData.chart_type,
    alternative_charts: responseData.alternative_charts || [],
    steps: responseData.steps || [],
    is_cached: responseData.is_cached || responseData.from_cache || false,
    insight: responseData.insight,
    data_interpretation: responseData.data_interpretation,
    fluctuation_analysis: responseData.fluctuation_analysis,
    followup_questions: responseData.followup_questions
  } as ChatResponse
}

export const generateSummary = async (data: SummaryRequest): Promise<SummaryResponse> => {
  return await http.post<SummaryResponse, SummaryRequest>('/chat/summary', data)
}

export const submitFeedback = async (data: FeedbackRequest): Promise<FeedbackResponse> => {
  return await http.post<FeedbackResponse, FeedbackRequest>('/chat/feedback', data)
}

// 导出数据
export interface ExportRequest {
  dataset_id: number
  question: string
  columns: string[]
  rows: any[]
}

export const exportToExcel = async (data: ExportRequest): Promise<Blob> => {
  const response = await http.post('/chat/export/excel', data, {
    responseType: 'blob'
  })
  return response as unknown as Blob
}

export const exportToCSV = async (data: ExportRequest): Promise<Blob> => {
  const response = await http.post('/chat/export/csv', data, {
    responseType: 'blob'
  })
  return response as unknown as Blob
}

// ========== 新增 API ==========

// 输入联想
export interface InputSuggestRequest {
  dataset_id: number
  partial_input: string
  limit?: number
}

export interface InputSuggestResponse {
  suggestions: string[]
}

export const suggestInput = async (data: InputSuggestRequest): Promise<InputSuggestResponse> => {
  return await http.post<InputSuggestResponse, InputSuggestRequest>('/chat/suggest-input', data)
}

// 后续推荐问题
export interface FollowupSuggestRequest {
  dataset_id: number
  current_question: string
  current_result: Record<string, any>
  limit?: number
}

export interface FollowupSuggestResponse {
  followup_questions: string[]
}

export const suggestFollowup = async (data: FollowupSuggestRequest): Promise<FollowupSuggestResponse> => {
  return await http.post<FollowupSuggestResponse, FollowupSuggestRequest>('/chat/suggest-followup', data)
}

// 增强导出
export interface EnhancedExportRequest {
  question: string
  sql?: string
  columns: string[]
  rows: any[]
  chart_type: string
  chart_data?: Record<string, any>
  insight?: string
  data_interpretation?: DataInterpretation
  fluctuation_analysis?: FluctuationAnalysis
  format: 'excel' | 'excel_with_chart' | 'pdf' | 'csv'
}

export const exportEnhanced = async (data: EnhancedExportRequest): Promise<Blob> => {
  const response = await http.post('/chat/export-result', data, {
    responseType: 'blob'
  })
  return response as unknown as Blob
}
