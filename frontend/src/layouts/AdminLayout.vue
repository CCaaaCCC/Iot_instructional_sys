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

        <button
          class="nav-section-label nav-group-toggle"
          :class="{ collapsed: teachingCollapsed }"
          type="button"
          @click="toggleGroup('teaching')"
        >
          教学管理
          <svg class="nav-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <div v-show="showTeaching" class="nav-group-items">
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
        </div>

        <button
          class="nav-section-label nav-group-toggle"
          :class="{ collapsed: systemCollapsed }"
          type="button"
          @click="toggleGroup('system')"
        >
          系统管理
          <svg class="nav-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <div v-show="!systemCollapsed" class="nav-group-items">
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
        </div>
      </nav>

      <div class="sidebar-footer" v-if="auth.user">
        <div class="sidebar-user" ref="userMenuRef">
          <button class="user-badge clickable" type="button" @click="userMenuOpen = !userMenuOpen">
            <span class="user-avatar">
              <img v-if="auth.user.avatar_url" :src="auth.user.avatar_url" :alt="auth.user.display_name || auth.user.username" />
              <span v-else>{{ (auth.user.display_name || auth.user.username).charAt(0).toUpperCase() }}</span>
            </span>
            {{ auth.user.display_name || auth.user.username }} · {{ roleLabel }}
            <svg style="margin-left:auto;opacity:.6" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>
          </button>
          <Transition name="modal-fade">
            <div v-if="userMenuOpen" class="user-menu">
              <button class="user-menu-item" type="button" @click="toggleThemeFromMenu">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                切换到{{ theme === 'dark' ? '浅色' : '深色' }}模式
              </button>
              <button class="user-menu-item danger" type="button" @click="handleLogout">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                退出登录
              </button>
            </div>
          </Transition>
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
          <button class="btn secondary sm icon-btn" type="button" title="刷新页面" @click="refreshPage">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            <span class="icon-btn-text">刷新</span>
          </button>
          <span class="topbar-user" :title="`${auth.user?.username} · ${roleLabel}`">
            <span class="topbar-avatar">
              <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" :alt="auth.user?.display_name || auth.user?.username" />
              <span v-else>{{ (auth.user?.display_name || auth.user?.username || '?').charAt(0).toUpperCase() }}</span>
            </span>
          </span>
          <button class="btn ghost sm mobile-only" type="button" title="切换主题" @click="toggle">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </button>
          <button class="btn ghost sm mobile-only" type="button" title="退出登录" @click="handleLogout">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </header>
      <RouterView />
    </main>
    <AiAssistant />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

// —— 菜单分组折叠 ——
const TEACHING_ROUTES = [
  'tasks', 'classrooms', 'groups', 'grading', 'analytics',
  'classroom-dashboard', 'courseware', 'resources', 'crops',
  'experiments', 'pest-diagnoses',
]
const teachingCollapsed = ref(localStorage.getItem('admin-nav-collapsed') !== 'false')
const systemCollapsed = ref(localStorage.getItem('admin-nav-system-collapsed') === 'true')

const showTeaching = computed(
  () => !teachingCollapsed.value || TEACHING_ROUTES.includes(String(route.name))
)

watch(teachingCollapsed, (value) => {
  localStorage.setItem('admin-nav-collapsed', String(value))
})
watch(systemCollapsed, (value) => {
  localStorage.setItem('admin-nav-system-collapsed', String(value))
})

function toggleGroup(group: 'teaching' | 'system') {
  if (group === 'teaching') {
    teachingCollapsed.value = !teachingCollapsed.value
  } else {
    systemCollapsed.value = !systemCollapsed.value
  }
}

// —— 用户菜单 ——
const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

function toggleThemeFromMenu() {
  toggle()
  userMenuOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    userMenuOpen.value = false
  }
}

watch(() => route.fullPath, () => {
  userMenuOpen.value = false
})

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))

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
  dashboard: '班级概览 · 任务进度 · 环境实时数据',
  devices: '管理节点、组件与设备令牌',
  sensors: '历史曲线与最新采集值',
  rules: '配置自动控制规则，追踪触发记录',
  logs: '操作、设备与规则日志统一审计',
  users: '维护管理员与教师账号',
  crops: '作物档案与生长阶段管理',
  tasks: '发布课堂任务，跟踪完成情况',
  classrooms: '创建班级，展开查看小组',
  groups: '管理小组、绑定设备、批量建号',
  grading: '批阅作业，打分并填写评语',
  analytics: '学习行为、提交统计与成绩趋势',
  'classroom-dashboard': '班级学情、小组排行与评分分布',
  courseware: '个人课件管理与公共课件库',
  resources: '向班级和小组发布教学资源',
  experiments: '科学实验全流程与观察记录',
  'pest-diagnoses': 'ESP32-CAM 病虫害诊断结果',
  'mcp-tools': '小智 AI 工具清单与调用日志',
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
const subtitle = computed(() => subtitleMap[String(route.name)] ?? '清晰、可靠、可扩展的教学管理台')
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
