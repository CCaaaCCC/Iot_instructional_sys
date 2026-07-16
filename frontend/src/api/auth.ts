import { http } from './http'
import type { TokenResponse, User } from '@/types'

export async function login(username: string, password: string) {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  const { data } = await http.post<TokenResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function fetchMe() {
  const { data } = await http.get<User>('/auth/me')
  return data
}
