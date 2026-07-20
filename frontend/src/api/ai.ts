import { http } from './http'
import { TOKEN_KEY } from '@/stores/auth'
import type { ChatSession, ChatMessage, ChatContext, AiQuota } from '@/types'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
// 开发环境下 SSE 直接访问后端，避免 Vite 代理在关闭流时触发 net::ERR_ABORTED
const sseBaseURL =
  import.meta.env.DEV && !baseURL.startsWith('http')
    ? 'http://127.0.0.1:8000/api/v1'
    : baseURL

/** 判断是否为 SSE 流正常关闭/被中止的已知错误。
 *
 * 部分浏览器在服务器关闭 SSE 连接时会抛出 `net::ERR_ABORTED`
 * 或 `Failed to fetch`，这不影响已接收到的完整回复，应静默忽略。
 */
export function isStreamClosedError(err: unknown): boolean {
  if (!err) return false
  if (err instanceof DOMException && err.name === 'AbortError') return true
  const msg = String((err as Error).message || '')
  return msg.includes('ERR_ABORTED') || msg.includes('Failed to fetch')
}

export interface StreamChatHandlers {
  onSession: (sessionId: number) => void
  onDelta: (content: string) => void
  onDone: (messageId: number, model: string) => void
  onError: (message: string) => void
}

export const aiApi = {
  createSession(title?: string) {
    return http.post<ChatSession>('/ai/sessions', title ? { title } : {})
  },
  listSessions(skip = 0, limit = 20) {
    return http.get<ChatSession[]>('/ai/sessions', { params: { skip, limit } })
  },
  getMessages(sessionId: number) {
    return http.get<ChatMessage[]>(`/ai/sessions/${sessionId}/messages`)
  },
  deleteSession(sessionId: number) {
    return http.delete(`/ai/sessions/${sessionId}`)
  },
  renameSession(sessionId: number, title: string) {
    return http.patch(`/ai/sessions/${sessionId}`, { title })
  },
  getQuota() {
    return http.get<AiQuota>('/ai/quota')
  },

  /** 流式聊天：XMLHttpRequest + onprogress 解析 SSE。
   *
   * 使用 XHR 而非 fetch 的原因：fetch 在服务器正常关闭 SSE 连接时，
   * Chromium 仍会在控制台/网络面板记录 net::ERR_ABORTED；
   * XHR 的 onprogress/onload 可以稳定接收流式数据，正常结束不会触发该错误。
   */
  streamChat(
    message: string,
    sessionId: number | null,
    context: ChatContext | null,
    handlers: StreamChatHandlers,
    signal?: AbortSignal,
  ): Promise<void> {
    const token = localStorage.getItem(TOKEN_KEY)
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      // buffer 存放尚未解析成完整 SSE 事件的尾部数据
      let buffer = ''
      // processedLength 跟踪已从 xhr.responseText 中提取的字节数
      // 注意：不能用 buffer.length 代替，因为 processChunk 解析完事件后
      // 会把 buffer 截短，此时 buffer.length 不再代表 responseText 的处理进度
      let processedLength = 0
      let receivedDone = false

      function processChunk(text: string) {
        buffer += text
        // 统一换行符，兼容代理可能返回的 \r\n\r\n
        buffer = buffer.replace(/\r\n/g, '\n')
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const dataLine = raw.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue
          try {
            const json = JSON.parse(dataLine.slice(6))
            switch (json.type) {
              case 'session':
                handlers.onSession(json.session_id)
                break
              case 'delta':
                handlers.onDelta(json.content)
                break
              case 'done':
                receivedDone = true
                handlers.onDone(json.message_id, json.model)
                break
              case 'error':
                handlers.onError(json.message)
                break
            }
          } catch {
            // 忽略解析失败的 SSE 帧
          }
        }
      }

      function handleNewData() {
        // responseText 是到目前为止收到的全部数据，
        // 只取 processedLength 之后的新增部分进行处理。
        const full = xhr.responseText
        if (full.length > processedLength) {
          processChunk(full.slice(processedLength))
          processedLength = full.length
        }
      }

      if (signal) {
        signal.addEventListener('abort', () => {
          if (xhr.readyState !== XMLHttpRequest.DONE) {
            xhr.abort()
          }
        })
      }

      xhr.open('POST', `${sseBaseURL}/ai/chat`)
      xhr.setRequestHeader('Content-Type', 'application/json')
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }

      xhr.onprogress = () => {
        handleNewData()
      }

      xhr.onload = () => {
        // 处理最后可能未触发 onprogress 的数据
        handleNewData()
        resolve()
      }

      xhr.onerror = () => {
        // 网络错误：只有在未收到 done 事件时才向上抛，避免正常关闭被误报
        if (!receivedDone) {
          reject(new Error('AI 服务请求失败'))
        } else {
          resolve()
        }
      }

      xhr.onabort = () => {
        // 用户主动中止，静默结束
        resolve()
      }

      xhr.send(JSON.stringify({ message, session_id: sessionId, context }))
    })
  },
}
