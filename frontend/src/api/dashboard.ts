import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  const response = await apiClient.get<Dashboard[]>('/dashboards/')
  return response.data
}

export const createDashboard = async (name: string, description?: string): Promise<Dashboard> => {
  const response = await apiClient.post<Dashboard>('/dashboards/', { name, description })
  return response.data
}

export const getDashboardDetail = async (id: number): Promise<Dashboard> => {
  const response = await apiClient.get<Dashboard>(`/dashboards/${id}`)
  return response.data
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
  const response = await apiClient.post<DashboardCard>(
    `/dashboards/${dashboardId}/cards`,
    cardData
  )
  return response.data
}

export const getCardData = async (cardId: number): Promise<CardData> => {
  const response = await apiClient.get<CardData>(`/dashboards/cards/${cardId}/data`)
  return response.data
}

export const deleteCard = async (cardId: number): Promise<void> => {
  await apiClient.delete(`/dashboards/cards/${cardId}`)
}

export const deleteDashboard = async (dashboardId: number): Promise<void> => {
  await apiClient.delete(`/dashboards/${dashboardId}`)
}
