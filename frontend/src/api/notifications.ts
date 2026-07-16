import { http } from './http'

export interface Notification {
  id: number
  user_id: number
  type: string
  title: string
  content: string
  link: string | null
  is_read: boolean
  created_at: string
}

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; skip?: number; limit?: number }) =>
    http.get<Notification[]>('/notifications', { params }).then(r => r.data),
  unreadCount: () =>
    http.get<{ count: number }>('/notifications/unread-count').then(r => r.data),
  markRead: (id: number) =>
    http.post<Notification>(`/notifications/${id}/read`).then(r => r.data),
  markAllRead: () =>
    http.post<{ updated: number }>('/notifications/read-all').then(r => r.data),
}
