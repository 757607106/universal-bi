/**
 * 文件上传相关API
 */
import { http } from '@/utils/http'

export interface FileUploadResponse {
  success: boolean
  message: string
  dataset_id: number
  dataset_name: string
  datasource_id: number
  table_name: string
  row_count: number
  column_count: number
}

export interface MultiFileUploadResponse {
  success: boolean
  message: string
  dataset_id: number
  dataset_name: string
  tables: Record<string, number>  // {table_name: row_count}
  total_files: number
  total_rows: number
  duckdb_path: string
}

export interface UploadedDatasetInfo {
  dataset_id: number
  dataset_name: string
  file_name: string
  row_count: number
  column_count: number
  created_at: string
  status: string
  is_uploaded: boolean
}

/**
 * 上传Excel/CSV文件
 */
export const uploadFile = async (file: File): Promise<FileUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  
  return await http.post<FileUploadResponse, FormData>('/upload/excel', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 批量上传多个 Excel/CSV 文件
 */
export const uploadMultipleFiles = async (
  files: File[],
  datasetName: string
): Promise<MultiFileUploadResponse> => {
  const formData = new FormData()
  
  // 添加所有文件
  files.forEach(file => {
    formData.append('files', file)
  })
  
  // 添加数据集名称
  formData.append('dataset_name', datasetName)
  
  return await http.post<MultiFileUploadResponse, FormData>('/upload/multi-files', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取已上传的数据集列表
 */
export const getUploadedDatasets = async (): Promise<UploadedDatasetInfo[]> => {
  return await http.get<UploadedDatasetInfo[]>('/upload/datasets')
}

