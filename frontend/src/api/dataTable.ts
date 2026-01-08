/**
 * 数据表管理API封装
 */
import { http } from '@/utils/http'

// ============ 类型定义 ============

export interface Folder {
  id: number
  name: string
  parent_id?: number
  owner_id?: number
  created_at: string
  updated_at: string
}

export interface FolderCreate {
  name: string
  parent_id?: number
}

export interface FolderUpdate {
  name?: string
  parent_id?: number
}

export interface TableField {
  id?: number
  data_table_id?: number
  field_name: string
  field_display_name: string
  field_type: 'text' | 'number' | 'datetime' | 'geo'
  date_format?: string
  null_display: string
  description?: string
  is_selected: boolean
  sort_order: number
  created_at?: string
  updated_at?: string
}

export interface DataTable {
  id: number
  display_name: string
  physical_table_name: string
  datasource_id: number
  folder_id?: number
  description?: string
  creation_method: 'excel_upload' | 'datasource_table'
  status: string
  row_count: number
  column_count: number
  owner_id?: number
  modifier_id?: number
  created_at: string
  updated_at: string
  fields?: TableField[]
}

export interface DataTableCreate {
  display_name: string
  datasource_id: number
  creation_method: 'excel_upload' | 'datasource_table'
  folder_id?: number
  description?: string
  source_table_name?: string
  fields?: TableField[]
}

export interface DataTableUpdate {
  display_name?: string
  folder_id?: number
  description?: string
  status?: string
}

export interface ExcelFieldPreview {
  field_name: string
  field_display_name: string
  field_type: string
  sample_values: any[]
}

export interface ExcelPreviewResponse {
  filename: string
  row_count: number
  column_count: number
  fields: ExcelFieldPreview[]
  preview_data: Record<string, any>[]
}

export interface DataQueryResponse {
  total: number
  page: number
  page_size: number
  data: Record<string, any>[]
  columns: TableField[]
}

// ============ 文件夹API ============

/**
 * 获取文件夹列表
 */
export const getFolders = (): Promise<Folder[]> => {
  return http.get('/data-tables/folders')
}

/**
 * 创建文件夹
 */
export const createFolder = (data: FolderCreate): Promise<Folder> => {
  return http.post('/data-tables/folders', data)
}

/**
 * 更新文件夹
 */
export const updateFolder = (id: number, data: FolderUpdate): Promise<Folder> => {
  return http.put(`/data-tables/folders/${id}`, data)
}

/**
 * 删除文件夹
 */
export const deleteFolder = (id: number): Promise<{ success: boolean; message: string }> => {
  return http.delete(`/data-tables/folders/${id}`)
}

// ============ 数据表API ============

/**
 * 预览Excel文件
 */
export const previewExcel = (file: File): Promise<ExcelPreviewResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/data-tables/preview-excel', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 创建数据表（从Excel上传）
 */
export const createDataTableFromExcel = (
  displayName: string,
  datasourceId: number,
  file: File,
  fields: TableField[],
  folderId?: number,
  description?: string
): Promise<DataTable> => {
  const formData = new FormData()
  formData.append('display_name', displayName)
  formData.append('creation_method', 'excel_upload')
  formData.append('file', file)
  
  // datasource_id是可选的，如果为0则后端会自动创建上传数据源
  if (datasourceId && datasourceId > 0) {
    formData.append('datasource_id', datasourceId.toString())
  }
  
  if (folderId) {
    formData.append('folder_id', folderId.toString())
  }
  if (description) {
    formData.append('description', description)
  }
  
  // 注意：这里简化了fields的传递，实际可能需要调整后端API
  return http.post('/data-tables/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 创建数据表（从数据源）
 */
export const createDataTableFromDatasource = (
  displayName: string,
  datasourceId: number,
  sourceTableName: string,
  fields: TableField[],
  folderId?: number,
  description?: string
): Promise<DataTable> => {
  return http.post('/data-tables/', {
    display_name: displayName,
    datasource_id: datasourceId,
    creation_method: 'datasource_table',
    source_table_name: sourceTableName,
    fields,
    folder_id: folderId,
    description
  })
}

/**
 * 获取数据表列表
 */
export const getDataTableList = (folderId?: number): Promise<DataTable[]> => {
  const params: Record<string, any> = {}
  if (folderId !== undefined) {
    params.folder_id = folderId
  }
  return http.get('/data-tables/', { params })
}

/**
 * 获取数据表详情
 */
export const getDataTable = (id: number): Promise<DataTable> => {
  return http.get(`/data-tables/${id}`)
}

/**
 * 更新数据表
 */
export const updateDataTable = (id: number, data: DataTableUpdate): Promise<DataTable> => {
  return http.put(`/data-tables/${id}`, data)
}

/**
 * 删除数据表
 */
export const deleteDataTable = (id: number): Promise<{ success: boolean; message: string }> => {
  return http.delete(`/data-tables/${id}`)
}

/**
 * 更新字段配置
 */
export const updateFields = (id: number, fields: TableField[]): Promise<DataTable> => {
  return http.put(`/data-tables/${id}/fields`, { fields })
}

/**
 * 查询表数据
 */
export const queryDataTable = (
  id: number,
  page: number = 1,
  pageSize: number = 20
): Promise<DataQueryResponse> => {
  return http.get(`/data-tables/${id}/data`, {
    params: { page, page_size: pageSize }
  })
}
