<template>
  <div class="grid" style="gap: 18px">
    <!-- 工具清单 -->
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">MCP 工具清单</h3>
          <div class="card-subtitle">小智 AI（ESP32-S3）可调用的 6 个工具，全部自动 scope 到设备 token 对应的小组</div>
        </div>
      </template>
      <div class="tools-grid">
        <article v-for="tool in tools" :key="tool.name" class="tool-card">
          <div class="tool-header">
            <code class="tool-name">{{ tool.name }}</code>
          </div>
          <p class="tool-desc">{{ tool.description }}</p>
          <div v-if="Object.keys(tool.parameters).length > 0" class="tool-params">
            <div class="params-label">参数：</div>
            <div v-for="(param, key) in tool.parameters" :key="key" class="param-item">
              <code class="param-key">{{ key }}</code>
              <span class="param-type">{{ param.type }}</span>
              <span v-if="param.enum" class="param-enum">[{{ param.enum.join(' / ') }}]</span>
              <span class="param-desc">{{ param.description }}</span>
            </div>
          </div>
          <div v-else class="tool-params">
            <span class="params-label">无参数（自动从设备 token 获取小组信息）</span>
          </div>
        </article>
      </div>
    </SectionCard>

    <!-- 调用日志 -->
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">调用日志</h3>
          <div class="card-subtitle">按时间倒序展示最近的 MCP 工具调用记录（仅记工具调用，不记对话原文）</div>
        </div>
        <div class="toolbar">
          <select v-model="logFilter.group_id" class="select" style="width: 140px" @change="loadLogs">
            <option value="">全部小组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <select v-model="logFilter.tool_name" class="select" style="width: 220px" @change="loadLogs">
            <option value="">全部工具</option>
            <option v-for="t in tools" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>
          <button class="btn secondary sm" @click="loadLogs">刷新</button>
        </div>
      </template>

      <div v-if="logsError" class="msg-error">{{ logsError }}</div>

      <EmptyState
        v-if="!logs.length"
        icon="inbox"
        title="暂无调用日志"
        desc="小智 AI 发起工具调用后，这里会记录参数、结果与耗时"
      />

      <table v-else class="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>小组</th>
            <th>工具</th>
            <th>参数</th>
            <th>结果</th>
            <th>耗时</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" :class="{ 'row-error': !log.success }">
            <td class="time-cell">{{ formatTime(log.created_at) }}</td>
            <td>{{ log.group_name || '#' + log.group_id }}</td>
            <td><code class="tool-name-inline">{{ log.tool_name }}</code></td>
            <td class="args-cell">{{ formatJson(log.arguments) }}</td>
            <td class="args-cell">{{ log.success ? formatJson(log.result) : (log.error_message || '-') }}</td>
            <td>{{ log.duration_ms }}ms</td>
            <td>
              <span class="badge" :class="log.success ? 'success' : 'danger'">
                <span class="badge-dot"></span> {{ log.success ? '成功' : '失败' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </SectionCard>

    <!-- 在线试用（仅管理员） -->
    <SectionCard v-if="isAdmin">
      <template #header>
        <div>
          <h3 class="card-title">在线试用</h3>
          <div class="card-subtitle">选用任意小组的设备 token 试用工具调用（便于调试，模拟小智 AI 行为）</div>
        </div>
      </template>

      <div class="trial-form">
        <div class="form-row">
          <label style="flex: 1">
            <div class="form-label">设备 Token 明文（从设备管理页创建/重置后复制）</div>
            <input v-model="trial.tokenStr" class="input" style="width: 100%" placeholder="粘贴设备 token 明文，如 esp32s3_g1_demo_token_seed_0001" />
          </label>
        </div>
        <div class="form-hint">
          提示：设备 token 明文仅在创建或重置时返回一次。请先在「设备管理 → 设备鉴权令牌」创建/重置令牌并复制明文。
        </div>

        <div class="form-row">
          <label>
            <div class="form-label">工具</div>
            <select v-model="trial.toolName" class="select" style="width: 320px">
              <option value="">请选择工具...</option>
              <option v-for="t in tools" :key="t.name" :value="t.name">{{ t.name }}</option>
            </select>
          </label>
        </div>

        <div v-if="trialParams.length > 0" class="form-row params-form">
          <div class="form-label">参数</div>
          <div v-for="param in trialParams" :key="param.key" class="param-input">
            <label>
              <span class="param-key-label">{{ param.key }}</span>
              <select v-if="param.enum" v-model="trial.arguments[param.key]" class="select" style="width: 160px">
                <option value="">请选择...</option>
                <option v-for="v in param.enum" :key="v" :value="v">{{ v }}</option>
              </select>
              <input v-else v-model="trial.arguments[param.key]" class="input" style="width: 160px" :placeholder="param.description" />
            </label>
          </div>
        </div>

        <div class="form-row">
          <button
            :class="['btn', 'primary', { loading: trial.loading }]"
            :disabled="!trial.tokenStr || !trial.toolName || trial.loading"
            @click="executeTrial"
          >
            执行调用
          </button>
        </div>

        <div v-if="trial.result" class="trial-result">
          <div class="form-label">调用结果</div>
          <pre class="result-pre" :class="{ 'result-error': !trial.result.success }">{{ JSON.stringify(trial.result, null, 2) }}</pre>
        </div>

        <div v-if="trial.error" class="msg-error" style="margin-top: 8px">{{ trial.error }}</div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { fetchMcpLogs, callMcpTool } from '@/api/mcp'
import { fetchGroups } from '@/api/groups'
import { useAuthStore } from '@/stores/auth'
import type { Group, McpToolDefinition, McpCallLogListItem, McpToolCallResponse } from '@/types'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

// 工具清单（静态定义，与后端 list_tools() 一致）
const tools: McpToolDefinition[] = [
  {
    name: 'get_latest_sensor_data',
    description: '获取本组的最新环境数据（气温、湿度、土壤温湿度、光照、pH）',
    parameters: {},
  },
  {
    name: 'control_components_by_type',
    description: "按类型控制本组所有执行器（如'打开风扇'会控制本组所有风扇）。类型可选: fan/pump/light",
    parameters: {
      component_type: { type: 'string', description: '执行器类型', enum: ['fan', 'pump', 'light'] },
      action: { type: 'string', description: '控制动作', enum: ['on', 'off', 'auto'] },
    },
  },
  {
    name: 'get_group_components',
    description: '查询本组所有执行器（风扇/水泵/补光灯）的当前状态',
    parameters: {},
  },
  {
    name: 'get_crop_status',
    description: '查询本组的作物生长状态',
    parameters: {},
  },
  {
    name: 'list_pending_tasks',
    description: '列出本组的未完成课堂任务',
    parameters: {
      limit: { type: 'integer', description: '返回条数上限，默认 5', default: 5 },
    },
  },
  {
    name: 'list_group_rules',
    description: '查询本组节点启用的自动控制规则',
    parameters: {
      enabled_only: { type: 'boolean', description: '是否仅返回启用的规则，默认 true', default: true },
    },
  },
]

// 日志
const logs = ref<McpCallLogListItem[]>([])
const logsError = ref('')
const groups = ref<Group[]>([])
const logFilter = reactive({
  group_id: '' as string | number,
  tool_name: '' as string,
})

async function loadLogs() {
  logsError.value = ''
  try {
    const params: { group_id?: number; tool_name?: string } = {}
    if (logFilter.group_id) params.group_id = Number(logFilter.group_id)
    if (logFilter.tool_name) params.tool_name = logFilter.tool_name
    logs.value = await fetchMcpLogs(params)
  } catch {
    logsError.value = '日志加载失败，请确认后端已启动。'
  }
}

// 在线试用
const trial = reactive({
  tokenStr: '' as string,
  toolName: '' as string,
  arguments: {} as Record<string, unknown>,
  loading: false,
  result: null as McpToolCallResponse | null,
  error: '',
})

const trialParams = computed(() => {
  if (!trial.toolName) return []
  const tool = tools.find((t) => t.name === trial.toolName)
  if (!tool) return []
  return Object.entries(tool.parameters).map(([key, val]) => ({
    key,
    ...val,
  }))
})

// 切换工具时重置参数
watch(() => trial.toolName, () => {
  const tool = tools.find((t) => t.name === trial.toolName)
  const args: Record<string, unknown> = {}
  if (tool) {
    for (const [key, param] of Object.entries(tool.parameters)) {
      args[key] = param.default !== undefined ? param.default : ''
    }
  }
  trial.arguments = args
  trial.result = null
  trial.error = ''
})

async function executeTrial() {
  if (!trial.tokenStr || !trial.toolName) return
  trial.loading = true
  trial.result = null
  trial.error = ''
  try {
    // 清理空字符串参数
    const cleanArgs: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(trial.arguments)) {
      if (v !== '' && v !== null && v !== undefined) {
        cleanArgs[k] = v
      }
    }
    trial.result = await callMcpTool(trial.toolName, cleanArgs, trial.tokenStr)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '调用失败'
    trial.error = msg.includes('401') ? '设备 Token 无效或已过期，请在设备管理页 reset 后填入新 token' : msg
  } finally {
    trial.loading = false
  }
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function formatJson(value: string | null) {
  if (!value) return '-'
  try {
    const parsed = JSON.parse(value)
    return JSON.stringify(parsed)
  } catch {
    return value.length > 100 ? value.slice(0, 100) + '...' : value
  }
}

onMounted(async () => {
  await loadLogs()
  try {
    groups.value = await fetchGroups()
  } catch { /* ignore */ }
})
</script>

<style scoped>
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}
.tool-card {
  padding: 14px 16px;
  background: var(--panel-hover);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.tool-header {
  margin-bottom: 6px;
}
.tool-name {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 2px 8px;
  border-radius: 4px;
}
.tool-name-inline {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--primary);
}
.tool-desc {
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
  margin: 6px 0 10px;
}
.tool-params {
  border-top: 1px dashed var(--line);
  padding-top: 8px;
}
.params-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.param-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin: 3px 0;
  flex-wrap: wrap;
}
.param-key {
  font-family: 'Consolas', 'Monaco', monospace;
  font-weight: 600;
  color: var(--text);
}
.param-type {
  font-size: 11px;
  color: var(--muted);
  background: var(--line);
  padding: 1px 6px;
  border-radius: 3px;
}
.param-enum {
  font-size: 11px;
  color: var(--warning);
}
.param-desc {
  font-size: 12px;
  color: var(--muted);
}
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}
.empty-state-icon {
  font-size: 36px;
  margin-bottom: 8px;
}
.time-cell {
  font-size: 12px;
  white-space: nowrap;
}
.args-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}
.row-error {
  background: var(--danger-soft);
}
.trial-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.form-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}
.form-row label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}
.form-hint {
  font-size: 12px;
  color: var(--muted);
  background: var(--panel-hover);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px dashed var(--line);
}
.params-form {
  flex-direction: column;
  align-items: flex-start;
  padding: 12px;
  background: var(--panel-hover);
  border-radius: 6px;
  border: 1px solid var(--line);
}
.param-input {
  display: inline-block;
  margin-right: 12px;
  margin-top: 6px;
}
.param-input label {
  display: flex;
  align-items: center;
  gap: 6px;
}
.param-key-label {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  font-weight: 600;
  min-width: 80px;
}
.trial-result {
  margin-top: 8px;
}
.result-pre {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  color: var(--text);
}
.result-pre.result-error {
  border-color: var(--danger);
  background: var(--danger-soft);
}
</style>
