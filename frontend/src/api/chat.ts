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
  data: {
    columns: string[] | null
    rows: any[] | null
  } | null
  chart_type: string
  steps?: string[]  // Execution steps tracking
}

export const sendChat = async (data: { dataset_id: number, question: string }) => {
  const response = await apiClient.post<any>('/chat/', data)
  // Adapt flat backend response to nested frontend interface
  return {
    answer_text: response.data.answer_text || response.data.summary,  // Handle clarification
    sql: response.data.sql,
    data: response.data.columns && response.data.rows ? {
      columns: response.data.columns,
      rows: response.data.rows
    } : null,
    chart_type: response.data.chart_type,
    steps: response.data.steps || []  // Include execution steps
  } as ChatResponse
}
