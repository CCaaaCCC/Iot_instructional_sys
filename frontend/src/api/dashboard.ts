import { http } from './http'
import type { ComponentSummaryItem, DashboardOverview } from '@/types'

export async function fetchDashboardOverview() {
  const { data } = await http.get<DashboardOverview>('/dashboard/overview')
  return data
}

export async function fetchComponentSummary() {
  const { data } = await http.get<ComponentSummaryItem[]>('/dashboard/component-summary')
  return data
}
