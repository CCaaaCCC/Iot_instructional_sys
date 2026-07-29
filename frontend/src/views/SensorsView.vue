<template>
  <div class="grid" style="gap: 18px">
    <div class="grid two-col">
      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">历史曲线</h3>
            <div class="card-subtitle">支持时间范围和节点筛选（已归一化显示，hover 查看真实数值）</div>
          </div>
          <div class="toolbar">
            <input v-model="filters.node_id" class="input" type="number" placeholder="node_id" style="width: 140px" />
            <input v-model="filters.limit" class="input" type="number" placeholder="条数" style="width: 100px" />
            <button class="btn secondary sm" @click="loadChart">刷新曲线</button>
          </div>
        </template>
        <div class="metric-filter">
          <button
            v-for="m in allMetrics"
            :key="m.value"
            class="metric-chip"
            :class="{ active: selectedMetrics.includes(m.value) }"
            @click="toggleMetric(m.value)"
            type="button"
          >
            {{ m.label }}
          </button>
        </div>
        <LineChart :data="chartData" />
      </SectionCard>

      <SectionCard>
        <template #header>
          <div>
            <h3 class="card-title">最新一条数据</h3>
            <div class="card-subtitle">查看最近上报值</div>
          </div>
          <span v-if="connected" class="badge success"><span class="badge-dot"></span> 实时</span>
          <span v-else class="badge muted"><span class="badge-dot"></span> 离线</span>
        </template>
        <div v-if="latest" class="grid" style="gap: 10px">
          <div class="badge success"><span class="badge-dot"></span> 节点 ID：{{ latest.node_id }}</div>
          <div class="badge"><span class="badge-dot"></span> 时间：{{ formatTime(latest.recorded_at) }}</div>
          <table class="table">
            <tbody>
              <tr><th>空气温度</th><td>{{ displayValue(latest.air_temp) }}</td></tr>
              <tr><th>空气湿度</th><td>{{ displayValue(latest.air_humidity) }}</td></tr>
              <tr><th>土壤湿度</th><td>{{ displayValue(latest.soil_humidity) }}</td></tr>
              <tr><th>光照强度</th><td>{{ displayValue(latest.light_intensity) }}</td></tr>
              <tr><th>土壤 pH</th><td>{{ displayValue(latest.soil_ph) }}</td></tr>
              <tr><th>CO₂浓度</th><td>{{ displayValue(latest.co2) }} ppm</td></tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
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
        <span v-if="connected" class="badge success"><span class="badge-dot"></span> 实时</span>
      </template>
      <table class="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>节点</th>
            <th>空气温度</th>
            <th>空气湿度</th>
            <th>土壤湿度</th>
            <th>光照强度</th>
            <th>土壤 pH</th>
            <th>CO₂浓度</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in history" :key="row.id">
            <td>{{ formatTime(row.recorded_at) }}</td>
            <td>{{ row.node_id }}</td>
            <td>{{ displayValue(row.air_temp) }}</td>
            <td>{{ displayValue(row.air_humidity) }}</td>
            <td>{{ displayValue(row.soil_humidity) }}</td>
            <td>{{ displayValue(row.light_intensity) }}</td>
            <td>{{ displayValue(row.soil_ph) }}</td>
            <td>{{ displayValue(row.co2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!history.length" class="empty-state">
        暂无历史记录
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import SectionCard from '@/components/SectionCard.vue'
import LineChart from '@/components/LineChart.vue'
import { fetchLatestSensorData, fetchSensorCharts, fetchSensorData } from '@/api/sensors'
import { useWebSocket } from '@/composables/useWebSocket'
import type { EChartsResponse, SensorData, SensorMetric } from '@/types'

const { connected, latestSensorData } = useWebSocket()

const metricLabelMap: Record<string, string> = {
  air_temp: '空气温度',
  air_humidity: '空气湿度',
  soil_humidity: '土壤湿度',
  light_intensity: '光照强度',
  soil_ph: '土壤pH',
  co2: 'CO₂浓度',
}

const allMetrics: { value: SensorMetric; label: string }[] = [
  { value: 'air_temp', label: '空气温度' },
  { value: 'air_humidity', label: '空气湿度' },
  { value: 'soil_humidity', label: '土壤湿度' },
  { value: 'light_intensity', label: '光照强度' },
  { value: 'soil_ph', label: '土壤pH' },
  { value: 'co2', label: 'CO₂浓度' },
]

const selectedMetrics = ref<SensorMetric[]>(allMetrics.map((m) => m.value))

function toggleMetric(metric: SensorMetric) {
  const idx = selectedMetrics.value.indexOf(metric)
  if (idx >= 0) {
    if (selectedMetrics.value.length > 1) {
      selectedMetrics.value.splice(idx, 1)
    }
  } else {
    selectedMetrics.value.push(metric)
  }
}

const history = ref<SensorData[]>([])
const latest = ref<SensorData | null>(null)
const chartData = ref<EChartsResponse | null>(null)
const error = ref('')

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
    const data = await fetchSensorCharts({
      node_id: filters.node_id ? Number(filters.node_id) : undefined,
      limit: Number(filters.limit) || 24,
      metrics: selectedMetrics.value,
    })
    // series.name 从英文映射为中文
    data.series = data.series.map((s) => ({
      ...s,
      name: metricLabelMap[s.name] || s.name,
    }))
    chartData.value = data
  } catch {
    error.value = '图表数据加载失败。'
  }
}

watch(selectedMetrics, loadChart, { deep: true })

watch(latestSensorData, (data) => {
  if (!data) return
  latest.value = data
  history.value.unshift(data)
  if (history.value.length > 100) history.value.pop()

  if (chartData.value) {
    const timestamp = new Date(data.recorded_at).toLocaleString('zh-CN')
    chartData.value.x.push(timestamp)
    chartData.value.x.shift()

    chartData.value.series.forEach((series) => {
      const metricMap: Record<string, number | null> = {
        '空气温度': data.air_temp,
        '空气湿度': data.air_humidity,
        '土壤湿度': data.soil_humidity,
        '光照强度': data.light_intensity,
        '土壤pH': data.soil_ph,
        'CO₂浓度': data.co2,
      }
      const value = metricMap[series.name]
      series.data.push(value ?? null)
      series.data.shift()
    })
  }
})

onMounted(async () => {
  await Promise.all([loadHistory(), loadLatest(), loadChart()])
})
</script>

<style scoped>
.metric-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.metric-chip {
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.metric-chip.active {
  background: var(--primary, #2d7d6e);
  border-color: var(--primary, #2d7d6e);
  color: #fff;
}
.metric-chip:hover {
  opacity: 0.85;
}
</style>
