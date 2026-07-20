import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { aiApi, isStreamClosedError } from '@/api/ai'
import type { ChatSession, ChatMessage, ChatContext, AiQuota } from '@/types'

/**
 * AI 助手 composable（非全局单例）。
 *
 * 每个布局组件（AdminLayout / StudentLayout）各持一份实例，互不干扰。
 * 管理抽屉开关、会话列表、消息历史、流式生成、配额查询。
 */
export function useAI() {
  const isOpen = ref(false)
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref<number | null>(null)
  const messages = ref<ChatMessage[]>([])
  const streaming = ref(false)
  const streamingContent = ref('')
  const quota = ref<AiQuota | null>(null)
  const error = ref<string | null>(null)
  const inputText = ref('')
  let abortController: AbortController | null = null

  const route = useRoute()

  /** 构建页面上下文：当前路由名 + 空数据字典（首版不深入采集） */
  function buildContext(): ChatContext | null {
    const name = String(route.name || route.path || 'unknown')
    return { route_name: name, page_data: {} }
  }

  async function openDrawer() {
    isOpen.value = true
    await Promise.all([refreshSessions(), refreshQuota()])
  }

  function closeDrawer() {
    isOpen.value = false
  }

  async function refreshSessions() {
    try {
      const resp = await aiApi.listSessions()
      sessions.value = resp.data
    } catch {
      // 静默失败，不打扰用户
    }
  }

  async function refreshQuota() {
    try {
      const resp = await aiApi.getQuota()
      quota.value = resp.data
    } catch {
      // 忽略
    }
  }

  async function newSession() {
    currentSessionId.value = null
    messages.value = []
    inputText.value = ''
    error.value = null
    await refreshSessions()
  }

  async function switchSession(id: number) {
    currentSessionId.value = id
    messages.value = []
    error.value = null
    try {
      const resp = await aiApi.getMessages(id)
      messages.value = resp.data
    } catch {
      // 忽略
    }
  }

  async function sendMessage() {
    const text = inputText.value.trim()
    if (!text || streaming.value) return
    inputText.value = ''
    error.value = null

    // 立即显示用户消息
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: text,
      model_used: null,
      created_at: new Date().toISOString(),
    })

    streaming.value = true
    streamingContent.value = ''
    abortController = new AbortController()

    try {
      await aiApi.streamChat(
        text,
        currentSessionId.value,
        buildContext(),
        {
          onSession: (sid) => {
            // 仅当当前无会话时设置（首次创建）
            if (currentSessionId.value === null) {
              currentSessionId.value = sid
            }
          },
          onDelta: (chunk) => {
            streamingContent.value += chunk
          },
          onDone: async (messageId, model) => {
            const finalContent = streamingContent.value
            messages.value.push({
              id: Date.now() + 1,
              role: 'assistant',
              content: finalContent,
              model_used: model,
              created_at: new Date().toISOString(),
            })
            streamingContent.value = ''
            streaming.value = false
            // 刷新会话列表与配额
            await Promise.all([refreshSessions(), refreshQuota()])
          },
          onError: (msg) => {
            error.value = msg
            streaming.value = false
            streamingContent.value = ''
          },
        },
        abortController.signal,
      )
    } catch (e: unknown) {
      // 用户主动中止或 SSE 流正常关闭导致的网络错误，均不显示错误提示
      if (!isStreamClosedError(e)) {
        error.value = 'AI 服务暂时不可用，请稍后重试'
      }
      streaming.value = false
      streamingContent.value = ''
    } finally {
      abortController = null
    }
  }

  function stopGeneration() {
    if (abortController) {
      abortController.abort()
      streaming.value = false
      // 已生成内容保留为 assistant 消息
      if (streamingContent.value) {
        messages.value.push({
          id: Date.now(),
          role: 'assistant',
          content: streamingContent.value + '\n\n[已停止生成]',
          model_used: null,
          created_at: new Date().toISOString(),
        })
        streamingContent.value = ''
      }
    }
  }

  async function deleteSession(id: number) {
    try {
      await aiApi.deleteSession(id)
      sessions.value = sessions.value.filter((s) => s.id !== id)
      if (currentSessionId.value === id) {
        await newSession()
      }
    } catch {
      // 忽略
    }
  }

  return {
    isOpen,
    sessions,
    currentSessionId,
    messages,
    streaming,
    streamingContent,
    quota,
    error,
    inputText,
    openDrawer,
    closeDrawer,
    newSession,
    switchSession,
    sendMessage,
    stopGeneration,
    deleteSession,
    refreshQuota,
    refreshSessions,
  }
}
