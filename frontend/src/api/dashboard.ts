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
