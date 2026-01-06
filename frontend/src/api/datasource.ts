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

export const testConnection = async (data: DataSourceForm) => {
  return await http.post<boolean, DataSourceForm>('/datasources/test', data)
}

export const addDataSource = async (data: DataSourceForm) => {
  return await http.post<DataSource, DataSourceForm>('/datasources/', data)
}

export const getDataSourceList = async () => {
  return await http.get<DataSource[], any>('/datasources/')
}

export const deleteDataSource = async (id: number) => {
  return await http.delete<boolean, any>(`/datasources/${id}`)
}

export const getTables = async (id: number) => {
  return await http.get<string[], any>(`/datasources/${id}/tables`)
}

export const previewTable = async (id: number, tableName: string) => {
  return await http.get<{ columns: { prop: string, label: string }[], rows: any[] }, any>(`/datasources/${id}/tables/${tableName}/preview`)
}
