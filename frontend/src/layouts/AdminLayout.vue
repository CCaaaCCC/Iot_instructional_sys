<template>
  <div class="page-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">棚</div>
        <div>
          <div class="brand-title">智慧大棚后台</div>
          <div class="brand-subtitle">Cultiva · Field Journal</div>
        </div>
      </div>

      <div class="nav-section-label">主菜单</div>
      <nav class="nav-list">
        <RouterLink v-if="canAccess('dashboard')" class="nav-item" :to="{ name: 'dashboard' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </span>
          仪表盘
        </RouterLink>
        <RouterLink v-if="canAccess('devices')" class="nav-item" to="/devices">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9z"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/></svg>
          </span>
          设备管理
        </RouterLink>
        <RouterLink v-if="canAccess('sensors')" class="nav-item" to="/sensors">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-9 4 18 3-9h4"/></svg>
          </span>
          传感器数据
        </RouterLink>
        <RouterLink v-if="canAccess('rules')" class="nav-item" to="/rules">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          </span>
          规则控制
        </RouterLink>
        <RouterLink v-if="canAccess('logs')" class="nav-item" to="/logs">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </span>
          日志中心
        </RouterLink>

        <div class="nav-section-label">教学管理</div>
        <RouterLink v-if="canAccess('tasks')" class="nav-item" to="/tasks">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </span>
          课堂任务
        </RouterLink>
        <RouterLink v-if="canAccess('classrooms')" class="nav-item" to="/classrooms">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21v-1a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v1"/><path d="M5 9V7a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/><path d="M3 9h18"/><path d="M3 13h18"/></svg>
          </span>
          班级管理
        </RouterLink>
        <RouterLink v-if="canAccess('groups')" class="nav-item" to="/groups">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </span>
          小组概览
        </RouterLink>
        <RouterLink v-if="canAccess('grading')" class="nav-item" to="/grading">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          </span>
          批阅中心
        </RouterLink>
        <RouterLink v-if="canAccess('analytics')" class="nav-item" to="/analytics">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          </span>
          学生画像
        </RouterLink>
        <RouterLink v-if="canAccess('classroom-dashboard')" class="nav-item" to="/classroom-dashboard">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
          </span>
          班级驾驶舱
        </RouterLink>
        <RouterLink v-if="canAccess('courseware')" class="nav-item" to="/courseware">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </span>
          课件库
        </RouterLink>
        <RouterLink v-if="canAccess('resources')" class="nav-item" to="/resources">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/></svg>
          </span>
          教学资源
        </RouterLink>
        <RouterLink v-if="canAccess('crops')" class="nav-item" to="/crops">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/></svg>
          </span>
          作物管理
        </RouterLink>
        <RouterLink v-if="canAccess('experiments')" class="nav-item" to="/experiments">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/></svg>
          </span>
          实验管理
        </RouterLink>
        <RouterLink v-if="canAccess('pest-diagnoses')" class="nav-item" to="/pest-diagnoses">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </span>
          病虫害诊断
        </RouterLink>

        <div class="nav-section-label">系统管理</div>
        <RouterLink v-if="canAccess('users')" class="nav-item" to="/users">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </span>
          用户权限
        </RouterLink>
        <RouterLink v-if="canAccess('mcp-tools')" class="nav-item" to="/mcp-tools">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect x="4" y="8" width="16" height="12" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
          </span>
          MCP 工具
        </RouterLink>
      </nav>

      <div class="sidebar-footer" v-if="auth.user">
        <button class="theme-toggle" @click="toggle" type="button">
          <span class="theme-toggle-icon">
            <svg v-if="theme === 'dark'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          </span>
          {{ theme === 'dark' ? '浅色模式' : '深色模式' }}
          <span class="theme-toggle-track"></span>
        </button>
        <div class="user-badge">
          <span class="user-avatar">{{ auth.user.username.charAt(0).toUpperCase() }}</span>
          {{ auth.user.username }} · {{ roleLabel }}
        </div>
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div>
          <h1 class="page-title">{{ title }}</h1>
          <p class="page-desc">{{ subtitle }}</p>
        </div>
        <div class="actions">
          <NotificationBell ref="notificationBellRef" />
          <button class="btn secondary sm" @click="refreshPage">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            刷新
          </button>
          <button class="btn danger sm" @click="handleLogout">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            退出
          </button>
        </div>
      </header>
      <RouterView />
    </main>
    <AiAssistant />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { useWebSocket } from '@/composables/useWebSocket'
import NotificationBell from '@/components/NotificationBell.vue'
import AiAssistant from '@/components/AiAssistant.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { theme, toggle } = useTheme()
const { latestNotification } = useWebSocket()
const notificationBellRef = ref<InstanceType<typeof NotificationBell> | null>(null)

// WebSocket 收到 notification 事件时刷新铃铛未读数
watch(latestNotification, () => {
  notificationBellRef.value?.refresh()
})

const titleMap: Record<string, string> = {
  dashboard: '仪表盘',
  devices: '设备管理',
  sensors: '传感器数据',
  rules: '规则控制',
  logs: '日志中心',
  users: '用户权限',
  crops: '作物管理',
  tasks: '课堂任务',
  classrooms: '班级管理',
  groups: '小组概览',
  grading: '批阅中心',
  analytics: '学生画像',
  'classroom-dashboard': '班级驾驶舱',
  courseware: '课件库',
  resources: '教学资源',
  experiments: '实验管理',
  'pest-diagnoses': '病虫害诊断',
  'mcp-tools': 'MCP 工具',
}

const subtitleMap: Record<string, string> = {
  dashboard: '查看班级概览、任务进度、待批阅提交与最新环境数据',
  devices: '管理设备节点和组件（风扇/水泵/补光灯/传感器）',
  sensors: '查看历史曲线和最新采集值',
  rules: '配置自动控制规则并追踪触发日志',
  logs: '统一查看操作日志、设备日志和规则日志',
  users: '管理员维护管理员/教师账号',
  crops: '维护作物档案与生长阶段信息',
  tasks: '管理课堂任务和教学安排',
  classrooms: '创建班级、选择科目、展开查看小组',
  groups: '管理小组、绑定设备节点、批量创建学生账号',
  grading: '批阅学生作业提交，打分并填写评语',
  analytics: '查看学生学习行为分析、提交统计与成绩趋势',
  'classroom-dashboard': '班级整体学情、小组表现排行、任务完成情况、评分分布',
  courseware: '管理个人课件，浏览公共课件库，按科目/年级筛选',
  resources: '发布教学资源到班级/小组，学生端实时可见',
  experiments: '创建科学实验、分配对照/实验组、查看观察记录',
  'pest-diagnoses': '查看 ESP32-CAM 视觉节点上传的植物病虫害诊断结果',
  'mcp-tools': '查看小智 AI 可调用的 MCP 工具清单、调用日志，在线试用调试',
}

const roleLabels: Record<string, string> = {
  admin: '管理员',
  teacher: '教师',
}

const roleAccess: Record<string, Array<string>> = {
  dashboard: ['admin', 'teacher'],
  devices: ['admin', 'teacher'],
  sensors: ['admin', 'teacher'],
  rules: ['admin', 'teacher'],
  logs: ['admin', 'teacher'],
  users: ['admin'],
  crops: ['admin', 'teacher'],
  tasks: ['admin', 'teacher'],
  classrooms: ['admin', 'teacher'],
  groups: ['admin', 'teacher'],
  grading: ['admin', 'teacher'],
  analytics: ['admin', 'teacher'],
  'classroom-dashboard': ['admin', 'teacher'],
  courseware: ['admin', 'teacher'],
  resources: ['admin', 'teacher'],
  experiments: ['admin', 'teacher'],
  'pest-diagnoses': ['admin', 'teacher'],
  'mcp-tools': ['admin', 'teacher'],
}

const title = computed(() => titleMap[String(route.name)] ?? '智慧大棚后台')
const subtitle = computed(() => subtitleMap[String(route.name)] ?? '稳定、清晰、可扩展的后台管理台')
const roleLabel = computed(() => roleLabels[auth.user?.role ?? ''] ?? auth.user?.role ?? '')

function canAccess(name: string): boolean {
  const role = auth.user?.role
  return !!role && (roleAccess[name]?.includes(role) ?? false)
}

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}

function refreshPage() {
  window.location.reload()
}
</script>
