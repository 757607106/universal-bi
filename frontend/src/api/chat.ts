import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface ChatResponse {
  answer_text: string
  sql: string
  data: {
    columns: string[]
    rows: any[]
  }
  chart_type: string
}

export const sendChat = async (data: { dataset_id: number, question: string }) => {
  const response = await apiClient.post<any>('/chat/', data)
  // Adapt flat backend response to nested frontend interface
  return {
    answer_text: response.data.summary,
    sql: response.data.sql,
    data: {
      columns: response.data.columns,
      rows: response.data.rows
    },
    chart_type: response.data.chart_type
  } as ChatResponse
}
