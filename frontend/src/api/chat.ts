import { http } from "@/utils/http"

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
  next_questions?: string[]  // Suggested follow-up questions
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
  conversation_history?: ConversationMessage[]
}) => {
  const responseData = await http.post<any, { 
    dataset_id: number, 
    question: string, 
    use_cache?: boolean,
    conversation_history?: ConversationMessage[]
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
    next_questions: responseData.next_questions || []
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
