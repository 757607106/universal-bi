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
  from_cache?: boolean  // Whether result is from cache
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

export const sendChat = async (data: { dataset_id: number, question: string }) => {
  const responseData = await http.post<any, { dataset_id: number, question: string }>('/chat/', data)
  // 直接返回后端数据，保留原始结构
  return {
    answer_text: responseData.answer_text || responseData.summary,
    sql: responseData.sql,
    columns: responseData.columns,  // 直接传递
    rows: responseData.rows,  // 直接传递
    data: null,  // 不再包装
    chart_type: responseData.chart_type,
    steps: responseData.steps || [],
    from_cache: responseData.from_cache || false
  } as ChatResponse
}

export const submitFeedback = async (data: FeedbackRequest): Promise<FeedbackResponse> => {
  return await http.post<FeedbackResponse, FeedbackRequest>('/chat/feedback', data)
}
