<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsResponse } from '@/types'
import { useTheme } from '@/composables/useTheme'

const props = defineProps<{
  data: EChartsResponse | null
}>()

const { theme } = useTheme()
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const darkPalette = ['#b8d68a', '#f0b878', '#e08868', '#e88080', '#8ab8d8', '#c9a8d8']
const lightPalette = ['#16a34a', '#d97706', '#2563eb', '#dc2626', '#7c3aed', '#0891b2']

function getChartColors() {
  return theme.value === 'light' ? lightPalette : darkPalette
}

function getChartOptions() {
  const isLight = theme.value === 'light'
  const palette = getChartColors()

  return {
    tooltip: {
      backgroundColor: isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(20, 16, 11, 0.92)',
      borderColor: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(240, 184, 120, 0.18)',
      borderWidth: 1,
      textStyle: {
        color: isLight ? '#1a1a2e' : '#f4ecd8',
        fontSize: 12,
      },
      axisPointer: {
        lineStyle: {
          color: isLight ? 'rgba(0, 0, 0, 0.1)' : 'rgba(240, 184, 120, 0.2)',
        },
      },
    },
    legend: {
      textStyle: {
        color: isLight ? '#4a4a6a' : '#d4c9a8',
        fontSize: 12,
      },
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 3,
      itemGap: 16,
    },
    xAxis: {
      axisLabel: {
        color: isLight ? '#6b7280' : '#9a8a6a',
        fontSize: 11,
      },
      axisLine: {
        lineStyle: {
          color: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(240, 184, 120, 0.14)',
        },
      },
      axisTick: { show: false },
    },
    yAxis: {
      axisLabel: {
        color: isLight ? '#6b7280' : '#9a8a6a',
        fontSize: 11,
      },
      splitLine: {
        lineStyle: {
          color: isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 220, 160, 0.05)',
        },
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
  }
}

function render() {
  if (!chart || !props.data) {
    return
  }
  const palette = getChartColors()
  const baseOptions = getChartOptions()

  // 归一化处理：每个 series 除以自己的 max * 100，避免量级差异压扁曲线
  const seriesMax = props.data.series.map((s) => {
    const validValues = (s.data.filter((v) => v !== null && v !== undefined && v !== 0) as number[])
    return validValues.length > 0 ? Math.max(...validValues) : 1
  })

  const normalizedSeries = props.data.series.map((s, i) => ({
    name: s.name,
    type: 'line' as const,
    smooth: true,
    showSymbol: false,
    data: s.data.map((v) => (v === null || v === undefined ? null : (v / seriesMax[i]) * 100)),
    lineStyle: {
      width: 2.5,
      color: palette[i % palette.length],
    },
    areaStyle: {
      opacity: 0.08,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: palette[i % palette.length] },
        { offset: 1, color: 'transparent' },
      ]),
    },
    emphasis: {
      lineStyle: {
        width: 3,
      },
    },
    itemStyle: {
      color: palette[i % palette.length],
    },
  }))

  chart.setOption({
    backgroundColor: 'transparent',
    ...baseOptions,
    tooltip: {
      ...baseOptions.tooltip,
      trigger: 'axis',
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        let result = params[0].axisValue + '<br/>'
        params.forEach((p: any) => {
          const originalValue = props.data?.series[p.seriesIndex]?.data[p.dataIndex]
          result += `${p.marker} ${p.seriesName}: ${originalValue ?? '-'}<br/>`
        })
        return result
      },
    },
    grid: {
      left: 44,
      right: 20,
      top: 48,
      bottom: 28,
    },
    xAxis: {
      ...baseOptions.xAxis,
      type: 'category',
      data: props.data.x,
    },
    yAxis: {
      ...baseOptions.yAxis,
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        ...baseOptions.yAxis.axisLabel,
        formatter: '{value}%',
      },
    },
    series: normalizedSeries,
  }, true)
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    render()
    window.addEventListener('resize', resize)
  }
})

watch(() => props.data, render, { deep: true })
watch(theme, render)

function resize() {
  chart?.resize()
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-box {
  width: 100%;
  min-height: 340px;
}
</style>
