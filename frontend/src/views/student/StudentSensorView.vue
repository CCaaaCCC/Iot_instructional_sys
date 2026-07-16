<template>
  <div class="content-area">
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="error" class="msg-error" style="margin-bottom: 12px">{{ error }}</div>
    <template v-else>
      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">最新环境数据</h2>
          <span v-if="connected" class="badge success"><span class="badge-dot"></span> 实时</span>
          <span v-else-if="latest" class="badge success"><span class="badge-dot"></span> 最新</span>
          <span v-else class="badge muted">暂无数据</span>
        </div>
        <div v-if="latest" class="sensor-grid">
          <div class="sensor-item">
            <div class="sensor-label">气温</div>
            <div class="sensor-value">{{ latest.air_temp?.toFixed(1) ?? '--' }}°C</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">空气湿度</div>
            <div class="sensor-value">{{ latest.air_humidity?.toFixed(1) ?? '--' }}%</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤温度</div>
            <div class="sensor-value">{{ latest.soil_temp?.toFixed(1) ?? '--' }}°C</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤湿度</div>
            <div class="sensor-value">{{ latest.soil_humidity?.toFixed(1) ?? '--' }}%</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">光照强度</div>
            <div class="sensor-value">{{ latest.light_intensity?.toFixed(0) ?? '--' }} lux</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤pH</div>
            <div class="sensor-value">{{ latest.soil_ph?.toFixed(1) ?? '--' }}</div>
          </div>
        </div>
        <div v-else class="empty-state">本组设备暂无传感器数据</div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">趋势图表</h2>
          <span v-if="echartsData" class="badge muted">最近 {{ echartsData.x.length }} 个数据点</span>
        </div>
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
        <div v-if="chartLoading" class="loading-state">图表加载中...</div>
        <div v-else-if="echartsData && echartsData.x.length > 0">
          <LineChart :data="echartsData" />
        </div>
        <div v-else class="empty-state">暂无图表数据</div>
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">历史数据</h2>
          <span class="badge muted">最近 {{ history.length }} 条</span>
        </div>
        <div v-if="history.length === 0" class="empty-state">暂无历史数据</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>采集时间</th>
                <th>气温(°C)</th>
                <th>空气湿度(%)</th>
                <th>土壤温度(°C)</th>
                <th>土壤湿度(%)</th>
                <th>光照(lux)</th>
                <th>pH</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in history" :key="row.id">
                <td>{{ formatTime(row.recorded_at) }}</td>
                <td>{{ row.air_temp?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.air_humidity?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.soil_temp?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.soil_humidity?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.light_intensity?.toFixed(0) ?? '--' }}</td>
                <td>{{ row.soil_ph?.toFixed(1) ?? '--' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import LineChart from '@/components/LineChart.vue'
import { fetchMyLatestSensorData, fetchMySensorData, fetchMySensorECharts } from '@/api/student'
import { useWebSocket } from '@/composables/useWebSocket'
import type { EChartsResponse, SensorData, SensorMetric } from '@/types'

const { connected, latestSensorData } = useWebSocket()

const allMetrics: { value: SensorMetric; label: string }[] = [
  { value: 'air_temp', label: '气温' },
  { value: 'air_humidity', label: '空气湿度' },
  { value: 'soil_temp', label: '土壤温度' },
  { value: 'soil_humidity', label: '土壤湿度' },
  { value: 'light_intensity', label: '光照' },
  { value: 'soil_ph', label: 'pH' },
]

const loading = ref(true)
const chartLoading = ref(false)
const latest = ref<SensorData | null>(null)
const history = ref<SensorData[]>([])
const echartsData = ref<EChartsResponse | null>(null)
const error = ref('')
const selectedMetrics = ref<SensorMetric[]>(allMetrics.map((m) => m.value))

function formatTime(iso: string): string {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

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

async function loadECharts() {
  chartLoading.value = true
  try {
    echartsData.value = await fetchMySensorECharts(selectedMetrics.value)
  } catch (err) {
    console.error('Failed to load echarts data:', err)
  } finally {
    chartLoading.value = false
  }
}

watch(selectedMetrics, loadECharts, { deep: true })

async function loadData() {
  loading.value = true
  try {
    const [l, h] = await Promise.all([
      fetchMyLatestSensorData(),
      fetchMySensorData(50),
    ])
    latest.value = l
    history.value = h
    await loadECharts()
  } catch (err) {
    error.value = '传感器数据加载失败。'
    console.error('Failed to load sensor data:', err)
  } finally {
    loading.value = false
  }
}

// WebSocket 实时更新
watch(latestSensorData, (data) => {
  if (!data) return
  latest.value = data
  history.value.unshift(data)
  if (history.value.length > 100) history.value.pop()
})

onMounted(loadData)
</script>
