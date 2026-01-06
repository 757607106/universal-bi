import axios from 'axios'
import { getTables as getDataSourceTables } from './datasource'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export interface Dataset {
  id: number
  name: string
  datasource_id: number | null
  collection_name: string
  schema_config: string[] | null
  training_status: 'pending' | 'training' | 'completed' | 'failed'
  last_trained_at: string | null
}

export interface DatasetCreate {
  name: string
  datasource_id: number
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getDatasetList = async () => {
  const response = await apiClient.get<Dataset[]>('/datasets/')
  return response.data
}

export const createDataset = async (data: DatasetCreate) => {
  const response = await apiClient.post<Dataset>('/datasets/', data)
  return response.data
}

export const updateDatasetTables = async (id: number, tables: string[]) => {
  const response = await apiClient.put<Dataset>(`/datasets/${id}/tables`, { schema_config: tables })
  return response.data
}

export const trainDataset = async (id: number) => {
  const response = await apiClient.post<any>(`/datasets/${id}/train`)
  return response.data
}

// Re-export or wrap the datasource table fetching
export const getDbTables = getDataSourceTables
