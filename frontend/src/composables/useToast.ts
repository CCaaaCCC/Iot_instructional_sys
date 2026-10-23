import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
  duration: number
}

/** 模块级单例：所有组件共享同一队列（与 useWebSocket 相同的模式） */
const toasts = ref<ToastItem[]>([])
let seed = 0
const timers = new Map<number, ReturnType<typeof setTimeout>>()

function remove(id: number) {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

function arm(item: ToastItem) {
  const timer = setTimeout(() => remove(item.id), item.duration)
  timers.set(item.id, timer)
}

function push(type: ToastType, message: string, duration = 3200): number {
  const id = ++seed
  const item: ToastItem = { id, type, message, duration }
  toasts.value = [...toasts.value, item]
  arm(item)
  return id
}

/** 鼠标悬停时暂停自动关闭，移出后重新计时 */
function pause(id: number) {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

function resume(id: number) {
  const item = toasts.value.find((entry) => entry.id === id)
  if (item && !timers.has(id)) {
    arm(item)
  }
}

export function useToast() {
  return {
    toasts,
    remove,
    pause,
    resume,
    success: (message: string, duration?: number) => push('success', message, duration),
    error: (message: string, duration?: number) => push('error', message, duration),
    info: (message: string, duration?: number) => push('info', message, duration),
    warning: (message: string, duration?: number) => push('warning', message, duration),
  }
}
