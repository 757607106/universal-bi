import { http } from "@/utils/http"

export interface Dashboard {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
  cards: DashboardCard[]
}

export interface DashboardCard {
  id: number
  dashboard_id: number
  title: string
  dataset_id: number
  sql: string
  chart_type: string
  layout?: {
    x: number
    y: number
    w: number
    h: number
  }
  created_at: string
}

export interface CardData {
  columns: string[]
  rows: any[]
}

export const getDashboards = async (): Promise<Dashboard[]> => {
  return await http.get<Dashboard[], any>('/dashboards/')
}

export const createDashboard = async (name: string, description?: string): Promise<Dashboard> => {
  return await http.post<Dashboard, { name: string, description?: string }>('/dashboards/', { name, description })
}

export const getDashboardDetail = async (id: number): Promise<Dashboard> => {
  return await http.get<Dashboard, any>(`/dashboards/${id}`)
}

export const addCardToDashboard = async (
  dashboardId: number,
  cardData: {
    title: string
    dataset_id: number
    sql: string
    chart_type: string
    layout?: any
  }
): Promise<DashboardCard> => {
  return await http.post<DashboardCard, any>(
    `/dashboards/${dashboardId}/cards`,
    cardData
  )
}

export const getCardData = async (cardId: number): Promise<CardData> => {
  return await http.get<CardData, any>(`/dashboards/cards/${cardId}/data`)
}

export const deleteCard = async (cardId: number): Promise<void> => {
  await http.delete<void, any>(`/dashboards/cards/${cardId}`)
}

export const deleteDashboard = async (dashboardId: number): Promise<void> => {
  await http.delete<void, any>(`/dashboards/${dashboardId}`)
}


// ============ 看板模板相关 API ============

export interface DashboardTemplate {
  id: number
  name: string
  description?: string
  source_dashboard_id?: number
  config: {
    cards: Array<{
      title: string
      dataset_id: number
      sql: string
      chart_type: string
      layout?: any
    }>
  }
  owner_id: number
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface DashboardTemplateListItem {
  id: number
  name: string
  description?: string
  is_public: boolean
  owner_id: number
  created_at: string
}

export interface CreateTemplateRequest {
  name: string
  description?: string
  is_public?: boolean
}

export interface UpdateTemplateRequest {
  name?: string
  description?: string
  is_public?: boolean
}

/**
 * 将看板保存为模板
 */
export const saveDashboardAsTemplate = async (
  dashboardId: number,
  data: CreateTemplateRequest
): Promise<DashboardTemplate> => {
  return await http.post<DashboardTemplate, CreateTemplateRequest>(
    `/dashboards/${dashboardId}/save-as-template`,
    data
  )
}

/**
 * 获取模板列表
 */
export const getTemplates = async (skip = 0, limit = 50): Promise<DashboardTemplateListItem[]> => {
  return await http.get<DashboardTemplateListItem[], any>('/dashboards/templates/', { params: { skip, limit } })
}

/**
 * 获取模板详情
 */
export const getTemplateDetail = async (templateId: number): Promise<DashboardTemplate> => {
  return await http.get<DashboardTemplate, any>(`/dashboards/templates/${templateId}`)
}

/**
 * 从模板创建看板
 */
export const createDashboardFromTemplate = async (
  templateId: number,
  name?: string
): Promise<Dashboard> => {
  const params = name ? { name } : {}
  return await http.post<Dashboard, any>(
    `/dashboards/templates/${templateId}/create-dashboard`,
    {},
    { params }
  )
}

/**
 * 更新模板
 */
export const updateTemplate = async (
  templateId: number,
  data: UpdateTemplateRequest
): Promise<DashboardTemplate> => {
  return await http.patch<DashboardTemplate, UpdateTemplateRequest>(
    `/dashboards/templates/${templateId}`,
    data
  )
}

/**
 * 删除模板
 */
export const deleteTemplate = async (templateId: number): Promise<void> => {
  await http.delete<void, any>(`/dashboards/templates/${templateId}`)
}
