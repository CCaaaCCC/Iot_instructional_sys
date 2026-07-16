import { ref } from 'vue'
import type { SensorData } from '@/types'

interface ComponentUpdate {
  component_id: number
  node_id: number
  type: string
  status: string
  triggered_by_rule: string
}

interface DeviceStatus {
  node_id: number
  online: boolean
  last_reported_at: string | null
}

export interface PestDiagnosisEvent {
  id: number
  group_id: number
  node_id: number
  image_url: string
  diagnosis_result: string
  diagnosis_label: string
  confidence: number
  suggestion: string | null
  created_at: string | null
}

// ---- Module-level singleton state (shared across all component instances) ----

const connected = ref(false)
const latestSensorData = ref<SensorData | null>(null)
const componentUpdates = ref<ComponentUpdate[]>([])
const deviceStatuses = ref<DeviceStatus[]>([])
const pestDiagnoses = ref<PestDiagnosisEvent[]>([])
const latestNotification = ref<unknown>(null)

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let heartbeatTimer: ReturnType<typeof setInterval> | null = null
let reconnectDelay = 1000
let destroyed = false

function connect() {
  if (destroyed || ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return

  const token = localStorage.getItem('greenhouse_token')
  if (!token) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const url = `${protocol}//${host}/ws?token=${token}`

  try {
    ws = new WebSocket(url)
  } catch {
    scheduleReconnect()
    return
  }

  ws.onopen = () => {
    connected.value = true
    reconnectDelay = 1000
    startHeartbeat()
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      switch (msg.type) {
        case 'sensor_data':
          latestSensorData.value = msg.data
          break
        case 'component_status':
          componentUpdates.value = [...componentUpdates.value, msg.data].slice(-50)
          break
        case 'device_status':
          deviceStatuses.value = [...deviceStatuses.value, msg.data].slice(-50)
          break
        case 'pest_diagnosis':
          pestDiagnoses.value = [...pestDiagnoses.value, msg.data].slice(-20)
          break
        case 'notification':
          latestNotification.value = msg.data
          break
      }
    } catch {
      // ignore malformed messages
    }
  }

  ws.onclose = (event) => {
    connected.value = false
    stopHeartbeat()
    ws = null
    // 认证失败不重连
    if (event.code === 4001 || event.code === 4003 || event.code === 1000) return
    scheduleReconnect()
  }

  ws.onerror = () => {
    // onclose will fire after this
  }
}

function scheduleReconnect() {
  if (destroyed || reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    reconnectDelay = Math.min(reconnectDelay * 2, 30000)
    connect()
  }, reconnectDelay)
}

function startHeartbeat() {
  heartbeatTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send('ping')
    }
  }, 30000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function disconnect() {
  destroyed = true
  stopHeartbeat()
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close(1000)
    ws = null
  }
  connected.value = false
}

/** 重置单例状态（登出时调用），使下次 useWebSocket() 重新建立连接 */
function reset() {
  disconnect()
  destroyed = false
  reconnectDelay = 1000
  latestSensorData.value = null
  componentUpdates.value = []
  deviceStatuses.value = []
  pestDiagnoses.value = []
  latestNotification.value = null
}

// 页面卸载时断开
window.addEventListener('beforeunload', disconnect)

// ---- Composable (returns shared singleton refs) ----

export function useWebSocket() {
  // 自动连接：如果尚未连接且未被销毁，尝试建立连接
  if (!destroyed && !ws) {
    connect()
  }

  return { connected, latestSensorData, componentUpdates, deviceStatuses, pestDiagnoses, latestNotification, disconnect, reset }
}
