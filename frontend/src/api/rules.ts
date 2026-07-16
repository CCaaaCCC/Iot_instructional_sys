import { http } from './http'
import type { Rule, RuleLog } from '@/types'

export async function fetchRules() {
  const { data } = await http.get<Rule[]>('/rules')
  return data
}

export async function createRule(payload: Partial<Rule>) {
  const { data } = await http.post<Rule>('/rules', payload)
  return data
}

export async function updateRule(ruleId: number, payload: Partial<Rule>) {
  const { data } = await http.patch<Rule>(`/rules/${ruleId}`, payload)
  return data
}

export async function toggleRule(ruleId: number) {
  const { data } = await http.post<Rule>(`/rules/${ruleId}/toggle`)
  return data
}

export async function deleteRule(ruleId: number) {
  await http.delete(`/rules/${ruleId}`)
}

export async function fetchRuleLogs(params?: { rule_id?: number }) {
  const { data } = await http.get<RuleLog[]>('/rules/logs', { params })
  return data
}
