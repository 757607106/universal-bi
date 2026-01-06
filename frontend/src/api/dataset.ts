import { http } from "@/utils/http"
import { getTables as getDataSourceTables } from './datasource'

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

export const getDatasetList = async () => {
  return await http.get<Dataset[], any>('/datasets/')
}

export const createDataset = async (data: DatasetCreate) => {
  return await http.post<Dataset, DatasetCreate>('/datasets/', data)
}

export const updateDatasetTables = async (id: number, tables: string[]) => {
  return await http.put<Dataset, { schema_config: string[] }>(`/datasets/${id}/tables`, { schema_config: tables })
}

export const trainDataset = async (id: number) => {
  return await http.post<any, any>(`/datasets/${id}/train`)
}

// Re-export or wrap the datasource table fetching
export const getDbTables = getDataSourceTables
