/**
 * 展示层枚举 → 中文文案映射。
 * 所有页面统一从此文件取 label，避免中英混杂与各页面重复定义。
 */

export const taskStatusLabels: Record<string, string> = {
  pending: '待开始',
  in_progress: '进行中',
  done: '已完成',
}

export const taskTypeLabels: Record<string, string> = {
  observation: '观察任务',
  experiment: '实验任务',
  maintenance: '维护任务',
}

export const courseSubjectLabels: Record<string, string> = {
  labor: '劳动课',
  science: '科学课',
}

export const componentTypeLabels: Record<string, string> = {
  sensor: '传感器',
  fan: '风扇',
  pump: '水泵',
  light: '补光灯',
}

export const componentStatusLabels: Record<string, string> = {
  on: '开启',
  off: '关闭',
  auto: '自动',
}

export const deviceTypeLabels: Record<string, string> = {
  esp32: '主控节点',
  esp32cam: '视觉相机',
  esp32s3: '小智语音',
  esp32s3_monitor: '监测屏',
}

export const diagnosisResultLabels: Record<string, string> = {
  tomato_healthy: '番茄健康',
  tomato_early_blight: '番茄早疫病',
  tomato_late_blight: '番茄晚疫病',
  strawberry_healthy: '草莓健康',
  strawberry_leaf_scorch: '草莓叶焦病',
}

export const experimentStatusLabels: Record<string, string> = {
  ongoing: '进行中',
  completed: '已完成',
}

export const experimentRoleLabels: Record<string, string> = {
  control: '对照组',
  experimental: '实验组',
}

export const ruleOperatorLabels: Record<string, string> = {
  '>': '大于',
  '>=': '大于等于',
  '<': '小于',
  '<=': '小于等于',
}

export const sensorMetricLabels: Record<string, string> = {
  air_temp: '空气温度',
  air_humidity: '空气湿度',
  soil_humidity: '土壤湿度',
  light_intensity: '光照强度',
  soil_ph: '土壤 pH',
  co2: 'CO₂ 浓度',
}

export const sensorMetricUnits: Record<string, string> = {
  air_temp: '°C',
  air_humidity: '%',
  soil_humidity: '%',
  light_intensity: 'lux',
  soil_ph: '',
  co2: 'ppm',
}

export const userRoleLabels: Record<string, string> = {
  admin: '管理员',
  teacher: '教师',
  student: '学生',
}

/** 安全取 label：找不到时返回中文占位而不是英文 key */
export function labelOf(map: Record<string, string>, value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  return map[value] ?? fallback
}

/** 相对时间：3 分钟前 / 2 小时前 / 昨天 */
export function relativeTime(input: string | null | undefined): string {
  if (!input) return '—'
  const time = new Date(input).getTime()
  if (Number.isNaN(time)) return '—'
  const diff = Date.now() - time
  if (diff < 60_000) return '刚刚'
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days === 1) return '昨天'
  if (days < 30) return `${days} 天前`
  return new Date(input).toLocaleDateString('zh-CN')
}

/** 字节数 → 可读大小 */
export function formatSize(bytes: number | null | undefined): string {
  if (!bytes || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
