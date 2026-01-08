import { http } from "@/utils/http"

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

export interface TableInfo {
  name: string
  columns: {
    name: string
    type: string
    nullable?: boolean
    default?: string | null
  }[]
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  error?: string
  error_type?: 'password_decrypt_failed' | 'access_denied' | 'connection_refused' | 'unknown_database' | 'connection_failed' | 'connection_error'
}

export const testConnection = async (data: DataSourceForm) => {
  return await http.post<boolean, DataSourceForm>('/datasources/test', data)
}

export const addDataSource = async (data: DataSourceForm) => {
  return await http.post<DataSource, DataSourceForm>('/datasources/', data)
}

export const updateDataSource = async (id: number, data: DataSourceForm) => {
  return await http.put<DataSource, DataSourceForm>(`/datasources/${id}`, data)
}

export const getDataSourceList = async () => {
  return await http.get<DataSource[], any>('/datasources/')
}

export const deleteDataSource = async (id: number) => {
  return await http.delete<boolean, any>(`/datasources/${id}`)
}

export const getTables = async (id: number) => {
  return await http.get<TableInfo[], any>(`/datasources/${id}/tables`)
}

export const previewTable = async (id: number, tableName: string) => {
  return await http.get<{ columns: { prop: string, label: string }[], rows: any[] }, any>(`/datasources/${id}/tables/${tableName}/preview`)
}

/**
 * 测试现有数据源的连接
 */
export const testExistingConnection = async (id: number) => {
  return await http.post<ConnectionTestResult, any>(`/datasources/${id}/test-connection`)
}

/**
 * 重新连接数据源（更新密码）
 */
export const reconnectDataSource = async (id: number, password: string) => {
  return await http.post<DataSource, { password: string }>(`/datasources/${id}/reconnect`, { password })
}
