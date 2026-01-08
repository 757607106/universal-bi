import { http } from "@/utils/http"

export interface ChatSession {
  id: number
  title: string
  dataset_id: number | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  session_id: number | null
  role: 'user' | 'assistant'
  question: string | null
  answer: string | null
  sql: string | null
  chart_type: string | null
  chart_data: {
    columns: string[]
    rows: any[]
  } | null
  insight: string | null
  created_at: string
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[]
}

export interface CreateSessionRequest {
  title?: string
  dataset_id?: number
}

export interface UpdateSessionRequest {
  title?: string
}

/**
 * 获取会话列表
 */
export const getSessions = async (skip = 0, limit = 50): Promise<ChatSession[]> => {
  return await http.get<ChatSession[], any>('/sessions/', { params: { skip, limit } })
}

/**
 * 创建新会话
 */
export const createSession = async (data: CreateSessionRequest = {}): Promise<ChatSession> => {
  return await http.post<ChatSession, CreateSessionRequest>('/sessions/', data)
}

/**
 * 获取会话详情（包含消息列表）
 */
export const getSessionDetail = async (sessionId: number): Promise<ChatSessionDetail> => {
  return await http.get<ChatSessionDetail, any>(`/sessions/${sessionId}`)
}

/**
 * 更新会话
 */
export const updateSession = async (sessionId: number, data: UpdateSessionRequest): Promise<ChatSession> => {
  return await http.patch<ChatSession, UpdateSessionRequest>(`/sessions/${sessionId}`, data)
}

/**
 * 删除会话
 */
export const deleteSession = async (sessionId: number): Promise<void> => {
  await http.delete<void, any>(`/sessions/${sessionId}`)
}

/**
 * 获取会话的消息列表
 */
export const getSessionMessages = async (sessionId: number, skip = 0, limit = 100): Promise<ChatMessage[]> => {
  return await http.get<ChatMessage[], any>(`/sessions/${sessionId}/messages`, { params: { skip, limit } })
}
