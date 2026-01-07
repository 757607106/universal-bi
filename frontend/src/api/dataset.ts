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

// Modeling APIs
export interface Field {
  name: string
  type: string
  nullable?: boolean
}

export interface TableNode {
  table_name: string
  fields: Field[]
}

export interface RelationshipEdge {
  source: string
  target: string
  source_col: string
  target_col: string
  type: string
  confidence?: string
}

export interface AnalyzeRelationshipsRequest {
  datasource_id: number
  table_names: string[]
}

export interface AnalyzeRelationshipsResponse {
  edges: RelationshipEdge[]
  nodes: TableNode[]
}

export interface CreateViewRequest {
  datasource_id: number
  view_name: string
  sql: string
}

export const analyzeRelationships = async (data: AnalyzeRelationshipsRequest) => {
  return await http.post<AnalyzeRelationshipsResponse, AnalyzeRelationshipsRequest>('/datasets/analyze', data)
}

export const createView = async (data: CreateViewRequest) => {
  return await http.post<{ message: string, view_name: string }, CreateViewRequest>('/datasets/create_view', data)
}

// Re-export or wrap the datasource table fetching
export const getDbTables = getDataSourceTables
