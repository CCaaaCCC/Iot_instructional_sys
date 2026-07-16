<template>
  <div class="grid" style="gap: 18px">
    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">上传传感器数据</h3>
          <div class="card-subtitle">用于联调 ESP32/模拟节点数据上报</div>
        </div>
      </template>
      <form class="form-grid" @submit.prevent="handleSubmit">
        <label>
          <div class="form-label">节点 ID</div>
          <input v-model.number="form.node_id" class="input" type="number" placeholder="node_id" />
        </label>
        <label>
          <div class="form-label">空气温度</div>
          <input v-model.number="form.air_temp" class="input" type="number" step="0.1" placeholder="℃" />
        </label>
        <label>
          <div class="form-label">空气湿度</div>
          <input v-model.number="form.air_humidity" class="input" type="number" step="0.1" placeholder="%" />
        </label>
        <label>
          <div class="form-label">土壤温度</div>
          <input v-model.number="form.soil_temp" class="input" type="number" step="0.1" placeholder="℃" />
        </label>
        <label>
          <div class="form-label">土壤湿度</div>
          <input v-model.number="form.soil_humidity" class="input" type="number" step="0.1" placeholder="%" />
        </label>
        <label>
          <div class="form-label">光照强度</div>
          <input v-model.number="form.light_intensity" class="input" type="number" step="0.1" placeholder="lux" />
        </label>
        <label>
          <div class="form-label">土壤 pH</div>
          <input v-model.number="form.soil_ph" class="input" type="number" step="0.1" placeholder="pH" />
        </label>
        <div style="display:flex;align-items:flex-end">
          <button class="btn primary">提交数据</button>
        </div>
      </form>
      <div v-if="message" class="msg-success">{{ message }}</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
    </SectionCard>

    <div class="grid two-col">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">历史曲线</h3>
            <div class="card-subtitle">支持时间范围和节点筛选</div>
          </div>
          <div class="toolbar">
            <input v-model="filters.node_id" class="input" type="number" placeholder="node_id" style="width: 140px" />
            <input v-model="filters.limit" class="input" type="number" placeholder="条数" style="width: 100px" />
            <button class="btn secondary sm" @click="loadChart">刷新曲线</button>
          </div>
        </template>
        <LineChart :data="chartData" />
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">最新一条数据</h3>
            <div class="card-subtitle">查看最近上报值</div>
          </div>
          <button class="btn secondary sm" @click="loadLatest">刷新</button>
          <span v-if="connected" class="badge success" style="margin-left:8px"><span class="badge-dot"></span> 实时</span>
          <span v-else class="badge muted" style="margin-left:8px"><span class="badge-dot"></span> 离线</span>
        </template>
        <div v-if="latest" class="grid" style="gap: 10px">
          <div class="badge success"><span class="badge-dot"></span> 节点 ID：{{ latest.node_id }}</div>
          <div class="badge"><span class="badge-dot"></span> 时间：{{ formatTime(latest.recorded_at) }}</div>
          <table class="table">
            <tbody>
              <tr><th>空气温度</th><td>{{ displayValue(latest.air_temp) }}</td></tr>
              <tr><th>空气湿度</th><td>{{ displayValue(latest.air_humidity) }}</td></tr>
              <tr><th>土壤温度</th><td>{{ displayValue(latest.soil_temp) }}</td></tr>
              <tr><th>土壤湿度</th><td>{{ displayValue(latest.soil_humidity) }}</td></tr>
              <tr><th>光照强度</th><td>{{ displayValue(latest.light_intensity) }}</td></tr>
              <tr><th>土壤 pH</th><td>{{ displayValue(latest.soil_ph) }}</td></tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          <div class="empty-state-icon">📡</div>
          暂无数据
        </div>
      </SectionCard>
    </div>

    <SectionCard>
      <template #header>
        <div>
          <h3 class="card-title">历史列表</h3>
          <div class="card-subtitle">查询与回放接口数据</div>
        </div>
        <button class="btn secondary sm" @click="loadHistory">刷新列表</button>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>节点</th>
            <th>空气温度</th>
            <th>空气湿度</th>
            <th>土壤温度</th>
            <th>土壤湿度</th>
            <th>光照强度</th>
            <th>土壤 pH</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in history" :key="row.id">
            <td>{{ formatTime(row.recorded_at) }}</td>
            <td>{{ row.node_id }}</td>
            <td>{{ displayValue(row.air_temp) }}</td>
            <td>{{ displayValue(row.air_humidity) }}</td>
            <td>{{ displayValue(row.soil_temp) }}</td>
            <td>{{ displayValue(row.soil_humidity) }}</td>
            <td>{{ displayValue(row.light_intensity) }}</td>
            <td>{{ displayValue(row.soil_ph) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!history.length" class="empty-state">
        <div class="empty-state-icon">📋</div>
        暂无历史记录
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import LineChart from '@/components/LineChart.vue'
import { createSensorData, fetchLatestSensorData, fetchSensorCharts, fetchSensorData } from '@/api/sensors'
import { useWebSocket } from '@/composables/useWebSocket'
import type { EChartsResponse, SensorData } from '@/types'

const { connected, latestSensorData } = useWebSocket()

const history = ref<SensorData[]>([])
const latest = ref<SensorData | null>(null)
const chartData = ref<EChartsResponse | null>(null)
const message = ref('')
const error = ref('')

const form = reactive({
  node_id: 1,
  air_temp: 25,
  air_humidity: 60,
  soil_temp: 22,
  soil_humidity: 48,
  light_intensity: 300,
  soil_ph: 6.5,
})

const filters = reactive({
  node_id: '',
  limit: 24,
})

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function displayValue(value: number | null) {
  return value === null || value === undefined ? '-' : value
}

async function loadHistory() {
  error.value = ''
  try {
    history.value = await fetchSensorData({
      node_id: filters.node_id ? Number(filters.node_id) : undefined,
      limit: Number(filters.limit) || 24,
    })
  } catch {
    error.value = '历史数据加载失败。'
  }
}

async function loadLatest() {
  error.value = ''
  try {
    latest.value = await fetchLatestSensorData(filters.node_id ? Number(filters.node_id) : undefined)
  } catch {
    error.value = '最新数据加载失败。'
  }
}

async function loadChart() {
  error.value = ''
  try {
    chartData.value = await fetchSensorCharts({
      node_id: filters.node_id ? Number(filters.node_id) : undefined,
      limit: Number(filters.limit) || 24,
    })
  } catch {
    error.value = '图表数据加载失败。'
  }
}

async function handleSubmit() {
  message.value = ''
  error.value = ''
  try {
    await createSensorData({
      node_id: Number(form.node_id),
      air_temp: form.air_temp,
      air_humidity: form.air_humidity,
      soil_temp: form.soil_temp,
      soil_humidity: form.soil_humidity,
      light_intensity: form.light_intensity,
      soil_ph: form.soil_ph,
    })
    message.value = '数据已提交，并会触发规则引擎（如有匹配规则）。'
    await Promise.all([loadHistory(), loadLatest(), loadChart()])
  } catch {
    error.value = '数据提交失败，请确认节点 ID 有效并且后端已启动。'
  }
}

// WebSocket 实时更新
watch(latestSensorData, (data) => {
  if (!data) return
  latest.value = data
  history.value.unshift(data)
  // 保持历史记录不超过 100 条
  if (history.value.length > 100) history.value.pop()
})

onMounted(async () => {
  await Promise.all([loadHistory(), loadLatest(), loadChart()])
})
</script>
