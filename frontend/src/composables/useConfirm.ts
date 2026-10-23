import { reactive } from 'vue'

export interface ConfirmOptions {
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  danger?: boolean
}

interface ConfirmState {
  open: boolean
  options: ConfirmOptions
}

/** 模块级单例状态，由 AppConfirm.vue 渲染 */
export const confirmState = reactive<ConfirmState>({
  open: false,
  options: { title: '' },
})

let resolver: ((value: boolean) => void) | null = null

function settle(value: boolean) {
  confirmState.open = false
  if (resolver) {
    resolver(value)
    resolver = null
  }
}

/**
 * 打开确认弹窗，返回用户选择结果。
 * 用法：const ok = await confirm({ title: '删除小组', message: '...', danger: true })
 */
export function confirm(options: ConfirmOptions): Promise<boolean> {
  // 已有弹窗未关闭时，先按取消处理旧请求，避免 Promise 悬挂
  if (resolver) {
    settle(false)
  }
  confirmState.options = { ...options }
  confirmState.open = true
  return new Promise<boolean>((resolve) => {
    resolver = resolve
  })
}

export function resolveConfirm(value: boolean) {
  settle(value)
}

export function useConfirm() {
  return confirm
}
