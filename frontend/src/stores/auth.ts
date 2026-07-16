import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchMe, login as loginRequest } from '../api/auth'
import { useWebSocket } from '../composables/useWebSocket'
import type { User } from '../types'

export const TOKEN_KEY = 'greenhouse_token'
export const USER_KEY = 'greenhouse_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref<User | null>(loadUser())
  const isReady = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  function loadUser() {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) {
      return null
    }
    try {
      return JSON.parse(raw) as User
    } catch {
      return null
    }
  }

  function persist() {
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
    if (user.value) {
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  async function login(username: string, password: string) {
    const response = await loginRequest(username, password)
    token.value = response.access_token
    persist()
    user.value = await fetchMe()
    persist()
  }

  async function syncMe() {
    if (!token.value) {
      user.value = null
      isReady.value = true
      persist()
      return
    }
    try {
      user.value = await fetchMe()
      persist()
    } catch {
      token.value = ''
      user.value = null
      persist()
    } finally {
      isReady.value = true
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    persist()
    // 重置 WebSocket 单例，断开连接并清理状态
    useWebSocket().reset()
  }

  function updateProfile(profile: Partial<User>) {
    if (user.value) {
      user.value = { ...user.value, ...profile }
      persist()
    }
  }

  return {
    token,
    user,
    isReady,
    isAuthenticated,
    login,
    logout,
    syncMe,
    updateProfile,
  }
})
