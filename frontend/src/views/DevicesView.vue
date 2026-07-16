<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">新增设备节点</h3>
          <div class="card-subtitle">创建 ESP32 设备节点，节点下可挂载风扇/水泵/补光灯/传感器组件</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreateNode">
        <label>
          <div class="form-label">节点名称</div>
          <input v-model="nodeForm.name" class="input" placeholder="如：1号棚主节点" />
        </label>
        <label>
          <div class="form-label">安装位置</div>
          <input v-model="nodeForm.location" class="input" placeholder="可选，如 A区-1号棚" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">创建节点</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">设备节点列表</h3>
          <div class="card-subtitle">展开节点查看组件，可控制执行器状态</div>
        </div>
        <div class="toolbar">
          <select v-model="filters.online" class="select" style="width: 140px" @change="loadNodes">
            <option value="">全部在线状态</option>
            <option value="true">在线</option>
            <option value="false">离线</option>
          </select>
          <button class="btn secondary sm" @click="loadNodes">刷新</button>
          <span v-if="connected" class="badge success" style="margin-left:8px"><span class="badge-dot"></span> 实时</span>
          <span v-else class="badge muted" style="margin-left:8px"><span class="badge-dot"></span> 离线</span>
        </div>
      </template>

      <div v-if="!nodes.length" class="empty-state">
        <div class="empty-state-icon">🔌</div>
        暂无设备节点
      </div>

      <div v-else class="grid" style="gap: 14px">
        <div v-for="node in nodes" :key="node.id" class="node-card" :class="{ offline: !node.online }">
          <div class="node-header" @click="toggleExpand(node.id)">
            <div class="node-info">
              <span class="badge" :class="node.online ? 'success' : 'danger'">
                <span class="badge-dot"></span> {{ node.online ? '在线' : '离线' }}
              </span>
              <strong>{{ node.name }}</strong>
              <span class="node-meta">ID: {{ node.id }}</span>
              <span v-if="node.location" class="node-meta">📍 {{ node.location }}</span>
              <span v-if="node.last_reported_at" class="node-meta">最近上报：{{ formatTime(node.last_reported_at) }}</span>
            </div>
            <div class="node-actions">
              <button class="btn secondary sm" @click.stop="toggleExpand(node.id)">
                {{ expandedNodeId === node.id ? '收起' : '展开' }}组件 ({{ componentCount(node.id) }})
              </button>
              <button class="btn danger sm" @click.stop="handleDeleteNode(node.id)">删除</button>
            </div>
          </div>

          <div v-if="expandedNodeId === node.id" class="node-body">
            <div class="component-section">
              <div class="component-section-header">
                <h4 class="component-section-title">组件列表</h4>
                <button class="btn primary sm" @click="openComponentForm(node.id)">+ 添加组件</button>
              </div>

              <div v-if="!getComponents(node.id).length" class="empty-state-sm">
                暂无组件，请添加风扇/水泵/补光灯或传感器
              </div>

              <table v-else class="table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>类型</th>
                    <th>状态</th>
                    <th>监控指标</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="comp in getComponents(node.id)" :key="comp.id">
                    <td><strong>{{ comp.name }}</strong></td>
                    <td><span class="badge info"><span class="badge-dot"></span> {{ componentTypeLabel(comp.type) }}</span></td>
                    <td>
                      <span class="badge" :class="statusClass(comp.status)">
                        <span class="badge-dot"></span> {{ statusLabel(comp.status) }}
                      </span>
                    </td>
                    <td>{{ comp.metric || '-' }}</td>
                    <td>
                      <div class="actions" v-if="comp.type !== 'sensor'">
                        <button class="btn secondary sm" @click="handleControl(node.id, comp.id, 'on')">开</button>
                        <button class="btn secondary sm" @click="handleControl(node.id, comp.id, 'off')">关</button>
                        <button class="btn secondary sm" @click="handleControl(node.id, comp.id, 'auto')">自动</button>
                      </div>
                      <span v-else class="node-meta">仅采集</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </SectionCard>

    <SectionCard v-if="showComponentForm">
      <template #header>
        <div>
          <h3 class="card-title">添加组件</h3>
          <div class="card-subtitle">为节点 #{{ componentForm.node_id }} 添加执行器或传感器</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleCreateComponent">
        <label>
          <div class="form-label">组件名称</div>
          <input v-model="componentForm.name" class="input" placeholder="如：1号风扇" />
        </label>
        <label>
          <div class="form-label">组件类型</div>
          <select v-model="componentForm.type" class="select">
            <option value="fan">fan - 风扇</option>
            <option value="pump">pump - 水泵</option>
            <option value="light">light - 补光灯</option>
            <option value="sensor">sensor - 传感器</option>
          </select>
        </label>
        <label v-if="componentForm.type === 'sensor'">
          <div class="form-label">监控指标</div>
          <select v-model="componentForm.metric" class="select">
            <option value="air_temp">air_temp - 空气温度</option>
            <option value="air_humidity">air_humidity - 空气湿度</option>
            <option value="soil_temp">soil_temp - 土壤温度</option>
            <option value="soil_humidity">soil_humidity - 土壤湿度</option>
            <option value="light_intensity">light_intensity - 光照强度</option>
            <option value="soil_ph">soil_ph - 土壤pH</option>
          </select>
        </label>
        <div style="display:flex;align-items:flex-end;gap:8px">
          <button class="btn primary">添加</button>
          <button class="btn secondary" @click="showComponentForm = false">取消</button>
        </div>
      </form>
    </SectionCard>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">设备鉴权令牌</h3>
          <div class="card-subtitle">为各小组的 ESP32 / ESP32-CAM / ESP32-S3 设备签发访问令牌，设备凭此令牌上报数据与调用接口</div>
        </div>
        <div class="toolbar">
          <button class="btn secondary sm" @click="loadDeviceTokens">刷新</button>
        </div>
      </template>

      <div v-if="revealedToken" class="token-reveal">
        <div class="token-reveal-header">
          <strong>令牌已生成（仅此一次展示，请立即复制）</strong>
          <button class="btn secondary sm" @click="revealedToken = null">关闭</button>
        </div>
        <code class="token-reveal-value">{{ revealedToken }}</code>
        <div style="margin-top:8px;display:flex;gap:8px">
          <button class="btn primary sm" @click="copyToken(revealedToken)">复制令牌</button>
        </div>
      </div>

      <form class="form-grid" style="margin-bottom:16px" @submit.prevent="handleCreateToken">
        <label>
          <div class="form-label">所属小组</div>
          <select v-model="tokenForm.group_id" class="select">
            <option :value="0" disabled>选择小组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}（#{{ g.id }}）</option>
          </select>
        </label>
        <label>
          <div class="form-label">设备类型</div>
          <select v-model="tokenForm.device_type" class="select">
            <option value="esp32">esp32 - 主控节点</option>
            <option value="esp32cam">esp32cam - 视觉节点</option>
            <option value="esp32s3">esp32s3 - 小智AI节点</option>
          </select>
        </label>
        <label>
          <div class="form-label">设备名称</div>
          <input v-model="tokenForm.device_name" class="input" placeholder="如：第1组-ESP32主控" />
        </label>
        <label>
          <div class="form-label">关联节点</div>
          <select v-model="tokenForm.node_id" class="select">
            <option :value="0" disabled>选择节点</option>
            <option v-for="n in nodes" :key="n.id" :value="n.id">{{ n.name }}（#{{ n.id }}）</option>
          </select>
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary" :disabled="tokenForm.group_id === 0 || tokenForm.node_id === 0">签发令牌</button>
        </div>
      </form>

      <div v-if="!deviceTokens.length" class="empty-state-sm">
        暂无设备令牌，请为小组签发
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>设备名称</th>
            <th>类型</th>
            <th>小组</th>
            <th>节点</th>
            <th>状态</th>
            <th>最后使用</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in deviceTokens" :key="t.id" :class="{ 'row-inactive': !t.is_active }">
            <td><strong>{{ t.device_name }}</strong></td>
            <td><span class="badge info"><span class="badge-dot"></span> {{ deviceTypeLabel(t.device_type) }}</span></td>
            <td>{{ t.group_name || '#' + t.group_id }}</td>
            <td>{{ t.node_name || '#' + t.node_id }}</td>
            <td>
              <span class="badge" :class="t.is_active ? 'success' : 'danger'">
                <span class="badge-dot"></span> {{ t.is_active ? '活跃' : '已吊销' }}
              </span>
            </td>
            <td>{{ formatTime(t.last_used_at) }}</td>
            <td>
              <div class="actions">
                <button class="btn secondary sm" @click="handleResetToken(t.id)">重置</button>
                <button v-if="t.is_active" class="btn warning sm" @click="handleRevokeToken(t.id)">吊销</button>
                <button class="btn danger sm" @click="handleDeleteToken(t.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import {
  controlComponent,
  createComponent,
  createNode,
  deleteNode,
  fetchComponents,
  fetchNodes,
} from '@/api/device_nodes'
import {
  createDeviceToken,
  deleteDeviceToken as removeDeviceToken,
  fetchDeviceTokens,
  resetDeviceToken,
  revokeDeviceToken,
} from '@/api/device_tokens'
import { fetchGroups } from '@/api/groups'
import { useWebSocket } from '@/composables/useWebSocket'
import type {
  Component,
  ComponentStatus,
  ComponentType,
  DeviceNode,
  DeviceTokenListItem,
  DeviceType,
  Group,
  SensorMetric,
} from '@/types'

const { connected, componentUpdates, deviceStatuses } = useWebSocket()

const nodes = ref<DeviceNode[]>([])
const componentsMap = ref<Record<number, Component[]>>({})
const expandedNodeId = ref<number | null>(null)
const showComponentForm = ref(false)
const message = ref('')
const error = ref('')

const nodeForm = reactive({ name: '', location: '' })
const componentForm = reactive({
  node_id: 0,
  name: '',
  type: 'fan' as ComponentType,
  metric: 'air_temp' as SensorMetric,
})
const filters = reactive({ online: '' })

// ---- 设备令牌 ----
const groups = ref<Group[]>([])
const deviceTokens = ref<DeviceTokenListItem[]>([])
const revealedToken = ref<string | null>(null)
const tokenForm = reactive({
  group_id: 0,
  device_type: 'esp32' as DeviceType,
  device_name: '',
  node_id: 0,
})

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function componentTypeLabel(type: ComponentType) {
  const map: Record<ComponentType, string> = {
    fan: '风扇',
    pump: '水泵',
    light: '补光灯',
    sensor: '传感器',
  }
  return `${type} - ${map[type]}`
}

function statusClass(status: ComponentStatus) {
  if (status === 'on') return 'success'
  if (status === 'auto') return 'warning'
  return 'danger'
}

function statusLabel(status: ComponentStatus) {
  if (status === 'on') return '开启'
  if (status === 'auto') return '自动'
  return '关闭'
}

function componentCount(nodeId: number) {
  return componentsMap.value[nodeId]?.length ?? 0
}

function getComponents(nodeId: number) {
  return componentsMap.value[nodeId] ?? []
}

async function loadNodes() {
  message.value = ''
  error.value = ''
  try {
    const params: { online?: boolean } = {}
    if (filters.online === 'true') params.online = true
    if (filters.online === 'false') params.online = false
    nodes.value = await fetchNodes(params)
    componentsMap.value = {}
    await Promise.all(
      nodes.value.map(async (node) => {
        componentsMap.value[node.id] = await fetchComponents(node.id)
      }),
    )
  } catch {
    error.value = '设备节点加载失败，请确认后端已启动。'
  }
}

async function toggleExpand(nodeId: number) {
  if (expandedNodeId.value === nodeId) {
    expandedNodeId.value = null
    return
  }
  expandedNodeId.value = nodeId
  if (!componentsMap.value[nodeId]) {
    try {
      componentsMap.value[nodeId] = await fetchComponents(nodeId)
    } catch {
      error.value = '组件加载失败。'
    }
  }
}

async function handleCreateNode() {
  message.value = ''
  error.value = ''
  try {
    await createNode({
      name: nodeForm.name,
      location: nodeForm.location || undefined,
    })
    message.value = '节点创建成功'
    nodeForm.name = ''
    nodeForm.location = ''
    await loadNodes()
  } catch {
    error.value = '节点创建失败，请确认名称唯一并检查后端状态。'
  }
}

async function handleDeleteNode(nodeId: number) {
  if (!confirm(`确认删除节点 #${nodeId}？此操作将一并移除其下所有组件。`)) return
  try {
    await deleteNode(nodeId)
    message.value = '节点已删除'
    if (expandedNodeId.value === nodeId) expandedNodeId.value = null
    await loadNodes()
  } catch {
    error.value = '节点删除失败。'
  }
}

function openComponentForm(nodeId: number) {
  componentForm.node_id = nodeId
  componentForm.name = ''
  componentForm.type = 'fan'
  componentForm.metric = 'air_temp'
  showComponentForm.value = true
}

async function handleCreateComponent() {
  message.value = ''
  error.value = ''
  try {
    const payload: { name: string; type: ComponentType; metric?: string } = {
      name: componentForm.name,
      type: componentForm.type,
    }
    if (componentForm.type === 'sensor') {
      payload.metric = componentForm.metric
    }
    await createComponent(componentForm.node_id, payload)
    message.value = '组件创建成功'
    showComponentForm.value = false
    componentsMap.value[componentForm.node_id] = await fetchComponents(componentForm.node_id)
  } catch {
    error.value = '组件创建失败，请确认字段有效。'
  }
}

async function handleControl(nodeId: number, componentId: number, action: ComponentStatus) {
  message.value = ''
  error.value = ''
  try {
    await controlComponent(nodeId, componentId, { action, message: `前端控制组件为 ${action}` })
    componentsMap.value[nodeId] = await fetchComponents(nodeId)
  } catch {
    error.value = '组件控制失败，请确认后端已连接。'
  }
}

// ---- 设备令牌管理 ----
function deviceTypeLabel(type: DeviceType) {
  const map: Record<DeviceType, string> = {
    esp32: 'ESP32 主控',
    esp32cam: 'ESP32-CAM 视觉',
    esp32s3: 'ESP32-S3 小智',
  }
  return map[type]
}

async function loadDeviceTokens() {
  try {
    deviceTokens.value = await fetchDeviceTokens()
  } catch {
    error.value = '设备令牌加载失败。'
  }
}

async function handleCreateToken() {
  message.value = ''
  error.value = ''
  if (!tokenForm.device_name.trim()) {
    error.value = '请输入设备名称'
    return
  }
  try {
    const result = await createDeviceToken({
      group_id: tokenForm.group_id,
      device_type: tokenForm.device_type,
      device_name: tokenForm.device_name,
      node_id: tokenForm.node_id,
    })
    revealedToken.value = result.token
    message.value = '令牌签发成功，请立即复制保存'
    tokenForm.device_name = ''
    await loadDeviceTokens()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '令牌签发失败，可能该组已有同类型设备令牌。'
  }
}

async function handleResetToken(tokenId: number) {
  if (!confirm(`确认重置令牌 #${tokenId}？旧令牌将立即失效。`)) return
  message.value = ''
  error.value = ''
  try {
    const result = await resetDeviceToken(tokenId)
    revealedToken.value = result.token
    message.value = '令牌已重置，请立即复制新令牌'
    await loadDeviceTokens()
  } catch {
    error.value = '令牌重置失败。'
  }
}

async function handleRevokeToken(tokenId: number) {
  if (!confirm(`确认吊销令牌 #${tokenId}？设备将无法再访问接口。`)) return
  message.value = ''
  error.value = ''
  try {
    await revokeDeviceToken(tokenId)
    message.value = '令牌已吊销'
    await loadDeviceTokens()
  } catch {
    error.value = '令牌吊销失败。'
  }
}

async function handleDeleteToken(tokenId: number) {
  if (!confirm(`确认彻底删除令牌 #${tokenId}？此操作不可恢复。`)) return
  message.value = ''
  error.value = ''
  try {
    await removeDeviceToken(tokenId)
    message.value = '令牌已删除'
    await loadDeviceTokens()
  } catch {
    error.value = '令牌删除失败（仅管理员可删除）。'
  }
}

async function copyToken(token: string) {
  try {
    await navigator.clipboard.writeText(token)
    message.value = '令牌已复制到剪贴板'
  } catch {
    error.value = '复制失败，请手动选择文本复制。'
  }
}

// WebSocket 实时更新组件状态
watch(componentUpdates, (updates) => {
  const latest = updates[updates.length - 1]
  if (!latest) return
  // 更新本地组件状态
  for (const comps of Object.values(componentsMap.value)) {
    const comp = comps.find(c => c.id === latest.component_id)
    if (comp) {
      comp.status = latest.status as ComponentStatus
    }
  }
})

// WebSocket 实时更新设备在线状态
watch(deviceStatuses, (statuses) => {
  const latest = statuses[statuses.length - 1]
  if (!latest) return
  const node = nodes.value.find(n => n.id === latest.node_id)
  if (node) {
    node.online = latest.online
    node.last_reported_at = latest.last_reported_at
  }
})

onMounted(async () => {
  await loadNodes()
  try {
    groups.value = await fetchGroups()
  } catch {
    // 忽略：小组加载失败不阻塞页面
  }
  await loadDeviceTokens()
})
</script>

<style scoped>
.node-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px 16px;
  background: var(--panel);
}
.node-card.offline {
  opacity: 0.7;
}
.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  flex-wrap: wrap;
}
.node-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.node-meta {
  color: var(--muted);
  font-size: 13px;
}
.node-actions {
  display: flex;
  gap: 8px;
}
.node-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}
.component-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.component-section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}
.empty-state-sm {
  padding: 16px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}
.token-reveal {
  margin-bottom: 16px;
  padding: 14px 16px;
  background: var(--accent-bg, #f0f7f5);
  border: 1px solid var(--primary, #2d7d6e);
  border-radius: var(--radius);
}
.token-reveal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.token-reveal-value {
  display: block;
  padding: 10px 12px;
  background: var(--panel, #fff);
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  word-break: break-all;
  border: 1px dashed var(--line, #ddd);
}
.row-inactive {
  opacity: 0.55;
}
</style>
