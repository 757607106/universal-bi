import { http } from "@/utils/http"
import { getTables as getDataSourceTables } from './datasource'

export interface Dataset {
  id: number
  name: string
  datasource_id: number | null
  collection_name: string
  schema_config: string[] | null
  status: 'pending' | 'training' | 'completed' | 'failed' | 'paused'
  training_status: 'pending' | 'training' | 'completed' | 'failed' | 'paused'  // 兼容旧字段
  process_rate: number
  error_msg: string | null
  last_train_at: string | null
  last_trained_at: string | null  // 兼容旧字段
  modeling_config?: {
    nodes: any[]
    edges: any[]
    viewport?: {
      x: number
      y: number
      zoom: number
    }
  }
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

// Training Progress APIs
export interface TrainingProgress {
  status: 'pending' | 'training' | 'completed' | 'failed' | 'paused'
  process_rate: number
  error_msg: string | null
  current_step: string
}

export interface TrainingLog {
  id: number
  content: string
  created_at: string
}

export const getTrainingProgress = async (id: number) => {
  return await http.get<TrainingProgress, any>(`/datasets/${id}/training/progress`)
}

export const getTrainingLogs = async (id: number, limit: number = 50) => {
  return await http.get<TrainingLog[], any>(`/datasets/${id}/training/logs?limit=${limit}`)
}

export const pauseTraining = async (id: number) => {
  return await http.post<{ message: string }, any>(`/datasets/${id}/training/pause`)
}

export const deleteTrainingData = async (id: number) => {
  return await http.delete<{ message: string }, any>(`/datasets/${id}/training`)
}

export const deleteDataset = async (id: number) => {
  return await http.delete<{ message: string }, any>(`/datasets/${id}`)
}

// Training Data APIs
export interface TrainingDataItem {
  id: string
  question: string
  sql: string
  training_data_type: 'sql' | 'ddl' | 'documentation'
  created_at?: string | null
}

export interface TrainingDataResponse {
  total: number
  items: TrainingDataItem[]
  page: number
  page_size: number
}

export const getTrainingData = async (id: number, page: number = 1, page_size: number = 20, type_filter?: string) => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: page_size.toString()
  })
  if (type_filter && type_filter !== 'all') {
    params.append('type_filter', type_filter)
  }
  return await http.get<TrainingDataResponse, any>(`/datasets/${id}/training/data?${params.toString()}`)
}

// Business Term APIs
export interface BusinessTerm {
  id: number
  dataset_id: number
  term: string
  definition: string
  created_at: string
}

export interface BusinessTermCreate {
  term: string
  definition: string
}

export const getBusinessTerms = async (datasetId: number) => {
  return await http.get<BusinessTerm[], any>(`/datasets/${datasetId}/terms`)
}

export const addBusinessTerm = async (datasetId: number, data: BusinessTermCreate) => {
  return await http.post<BusinessTerm, BusinessTermCreate>(`/datasets/${datasetId}/terms`, data)
}

export const deleteBusinessTerm = async (termId: number) => {
  return await http.delete<{ message: string }, any>(`/datasets/terms/${termId}`)
}

// QA Training APIs
export interface TrainQARequest {
  question: string
  sql: string
}

export const trainQAPair = async (datasetId: number, data: TrainQARequest) => {
  return await http.post<{ message: string }, TrainQARequest>(`/datasets/${datasetId}/training/qa`, data)
}

// Documentation Training APIs  
export interface TrainDocRequest {
  content: string
  doc_type?: string
}

export const trainDocumentation = async (datasetId: number, data: TrainDocRequest) => {
  return await http.post<{ message: string }, TrainDocRequest>(`/datasets/${datasetId}/training/doc`, data)
}

export const updateModelingConfig = async (id: number, config: any) => {
  return await http.put<{ message: string, modeling_config: any }, any>(`/datasets/${id}/modeling-config`, config)
}

export const getDataset = async (id: number) => {
  return await http.get<Dataset, any>(`/datasets/${id}`)
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
