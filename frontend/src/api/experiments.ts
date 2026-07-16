import { http } from './http'
import type { Experiment, ExperimentGroup, ExperimentObservation } from '@/types'

export async function fetchExperiments(params?: { class_id?: number }) {
  const { data } = await http.get<Experiment[]>('/experiments', { params })
  return data
}

export async function getExperiment(id: number) {
  const { data } = await http.get<Experiment>(`/experiments/${id}`)
  return data
}

export async function createExperiment(payload: Partial<Experiment>) {
  const { data } = await http.post<Experiment>('/experiments', payload)
  return data
}

export async function updateExperiment(id: number, payload: Partial<Experiment>) {
  const { data } = await http.patch<Experiment>(`/experiments/${id}`, payload)
  return data
}

export async function deleteExperiment(id: number) {
  await http.delete(`/experiments/${id}`)
}

export async function fetchExperimentGroups(experimentId: number) {
  const { data } = await http.get<ExperimentGroup[]>(`/experiments/${experimentId}/groups`)
  return data
}

export async function addExperimentGroup(experimentId: number, payload: { group_id: number; role: string; variable_target?: string | null }) {
  const { data } = await http.post<ExperimentGroup>(`/experiments/${experimentId}/groups`, payload)
  return data
}

export async function removeExperimentGroup(experimentId: number, groupId: number) {
  await http.delete(`/experiments/${experimentId}/groups/${groupId}`)
}

export async function fetchObservations(experimentId: number, params?: { student_id?: number }) {
  const { data } = await http.get<ExperimentObservation[]>(`/experiments/${experimentId}/observations`, { params })
  return data
}

export async function createObservation(experimentId: number, payload: { sensor_data_id?: number | null; content?: string | null }) {
  const { data } = await http.post<ExperimentObservation>(`/experiments/${experimentId}/observations`, payload)
  return data
}
