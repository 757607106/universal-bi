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
 * 获取已上传的数据集列表
 */
export const getUploadedDatasets = async (): Promise<UploadedDatasetInfo[]> => {
  return await http.get<UploadedDatasetInfo[]>('/upload/datasets')
}

