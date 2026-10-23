<template>
  <div class="content-area">
    <div v-if="loading" class="content-area">
      <div class="skeleton card"></div>
      <div class="skeleton card"></div>
    </div>
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
            <div class="sensor-hint">{{ comfortTemp(latest.air_temp) }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">空气湿度</div>
            <div class="sensor-value">{{ latest.air_humidity?.toFixed(1) ?? '--' }}%</div>
            <div class="sensor-hint">{{ comfortHumidity(latest.air_humidity) }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤湿度</div>
            <div class="sensor-value">{{ latest.soil_humidity?.toFixed(1) ?? '--' }}%</div>
            <div class="sensor-hint">{{ comfortSoil(latest.soil_humidity) }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">光照强度</div>
            <div class="sensor-value">{{ latest.light_intensity?.toFixed(0) ?? '--' }} lux</div>
            <div class="sensor-hint">{{ comfortLight(latest.light_intensity) }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">土壤pH</div>
            <div class="sensor-value">{{ latest.soil_ph?.toFixed(1) ?? '--' }}</div>
            <div class="sensor-hint">{{ comfortPh(latest.soil_ph) }}</div>
          </div>
          <div class="sensor-item">
            <div class="sensor-label">CO₂浓度</div>
            <div class="sensor-value">{{ latest.co2?.toFixed(0) ?? '--' }} ppm</div>
            <div class="sensor-hint">{{ comfortCo2(latest.co2) }}</div>
          </div>
        </div>
        <EmptyState
          v-else
          icon="chart"
          title="本组设备暂无传感器数据"
          desc="设备上报后，这里会显示大棚的实时环境"
        />
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
        <div v-if="chartLoading" class="skeleton card"></div>
        <div v-else-if="echartsData && echartsData.x.length > 0">
          <LineChart :data="echartsData" />
        </div>
        <EmptyState v-else icon="chart" title="暂无图表数据" desc="等待设备上报更多环境数据" />
      </section>

      <section class="content-card">
        <div class="card-header">
          <h2 class="card-title">历史数据</h2>
          <span class="badge muted">最近 {{ history.length }} 条</span>
        </div>
        <EmptyState v-if="history.length === 0" icon="inbox" title="暂无历史数据" desc="设备上报后，历史记录会显示在这里" />
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>采集时间</th>
                <th>气温(°C)</th>
                <th>空气湿度(%)</th>
                <th>土壤湿度(%)</th>
                <th>光照(lux)</th>
                <th>pH</th>
                <th>CO₂(ppm)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in history" :key="row.id">
                <td>{{ formatTime(row.recorded_at) }}</td>
                <td>{{ row.air_temp?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.air_humidity?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.soil_humidity?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.light_intensity?.toFixed(0) ?? '--' }}</td>
                <td>{{ row.soil_ph?.toFixed(1) ?? '--' }}</td>
                <td>{{ row.co2?.toFixed(0) ?? '--' }}</td>
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
import EmptyState from '@/components/EmptyState.vue'
import { fetchMyLatestSensorData, fetchMySensorData, fetchMySensorECharts } from '@/api/student'
import { useWebSocket } from '@/composables/useWebSocket'
import type { EChartsResponse, SensorData, SensorMetric } from '@/types'

const { connected, latestSensorData } = useWebSocket()

const metricLabelMap: Record<string, string> = {
  air_temp: '气温',
  air_humidity: '空气湿度',
  soil_humidity: '土壤湿度',
  light_intensity: '光照',
  soil_ph: 'pH',
  co2: 'CO₂浓度',
}

const allMetrics: { value: SensorMetric; label: string }[] = [
  { value: 'air_temp', label: '气温' },
  { value: 'air_humidity', label: '空气湿度' },
  { value: 'soil_humidity', label: '土壤湿度' },
  { value: 'light_intensity', label: '光照' },
  { value: 'soil_ph', label: 'pH' },
  { value: 'co2', label: 'CO₂浓度' },
]

const loading = ref(true)
const chartLoading = ref(false)
const latest = ref<SensorData | null>(null)
const history = ref<SensorData[]>([])
const echartsData = ref<EChartsResponse | null>(null)
const error = ref('')
const selectedMetrics = ref<SensorMetric[]>(allMetrics.map((m) => m.value))

function comfortTemp(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 15) return '偏凉，植物长得慢'
  if (value <= 28) return '很舒适'
  return '偏热，注意通风'
}

function comfortHumidity(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 40) return '偏干'
  if (value <= 70) return '很舒适'
  return '偏湿，注意通风'
}

function comfortSoil(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 30) return '偏干，可能需要浇水'
  if (value <= 60) return '湿度刚好'
  return '偏湿，小心烂根'
}

function comfortLight(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 300) return '有点暗'
  if (value <= 800) return '光照充足'
  return '偏强，注意遮阴'
}

function comfortPh(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 5.5) return '偏酸'
  if (value <= 7) return '酸碱适宜'
  return '偏碱'
}

function comfortCo2(value: number | null | undefined): string {
  if (value == null) return '暂无读数'
  if (value < 400) return '偏低'
  if (value <= 800) return '浓度适宜'
  return '偏高，注意通风'
}

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
    const data = await fetchMySensorECharts(selectedMetrics.value)
    // series.name 从英文映射为中文
    data.series = data.series.map((s) => ({
      ...s,
      name: metricLabelMap[s.name] || s.name,
    }))
    echartsData.value = data
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

  if (echartsData.value) {
    const timestamp = new Date(data.recorded_at).toLocaleString('zh-CN')
    echartsData.value.x.push(timestamp)
    echartsData.value.x.shift()

    echartsData.value.series.forEach((series) => {
      const metricMap: Record<string, number | null> = {
        '气温': data.air_temp,
        '空气湿度': data.air_humidity,
        '土壤湿度': data.soil_humidity,
        '光照': data.light_intensity,
        'pH': data.soil_ph,
        'CO₂浓度': data.co2,
      }
      const value = metricMap[series.name]
      series.data.push(value ?? null)
      series.data.shift()
    })
  }
})

onMounted(loadData)
</script>
