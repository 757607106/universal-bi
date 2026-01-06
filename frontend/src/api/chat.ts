import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  const response = await apiClient.post<any>('/chat/', data)
  // 直接返回后端数据，保留原始结构
  return {
    answer_text: response.data.answer_text || response.data.summary,
    sql: response.data.sql,
    columns: response.data.columns,  // 直接传递
    rows: response.data.rows,  // 直接传递
    data: null,  // 不再包装
    chart_type: response.data.chart_type,
    steps: response.data.steps || [],
    from_cache: response.data.from_cache || false
  } as ChatResponse
}

export const submitFeedback = async (data: FeedbackRequest): Promise<FeedbackResponse> => {
  const response = await apiClient.post<FeedbackResponse>('/chat/feedback', data)
  return response.data
}
