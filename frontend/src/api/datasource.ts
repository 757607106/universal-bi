import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export interface DataSourceForm {
  name: string
  type: string
  host: string
  port: number
  database_name: string
  username: string
  password?: string
}

export interface DataSource extends DataSourceForm {
  id: number
  password_encrypted?: string
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const testConnection = async (data: DataSourceForm) => {
  const response = await apiClient.post<boolean>('/datasources/test', data)
  return response.data
}

export const addDataSource = async (data: DataSourceForm) => {
  const response = await apiClient.post<DataSource>('/datasources/', data)
  return response.data
}

export const getDataSourceList = async () => {
  const response = await apiClient.get<DataSource[]>('/datasources/')
  return response.data
}

export const deleteDataSource = async (id: number) => {
  const response = await apiClient.delete<boolean>(`/datasources/${id}`)
  return response.data
}

export const getTables = async (id: number) => {
  const response = await apiClient.get<string[]>(`/datasources/${id}/tables`)
  return response.data
}

export const previewTable = async (id: number, tableName: string) => {
  const response = await apiClient.get<{ columns: { prop: string, label: string }[], rows: any[] }>(`/datasources/${id}/tables/${tableName}/preview`)
  return response.data
}
