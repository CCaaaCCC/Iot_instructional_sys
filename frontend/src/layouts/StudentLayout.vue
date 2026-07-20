<template>
  <div class="page-shell student-shell">
    <aside class="sidebar student-sidebar">
      <div class="brand">
        <div class="brand-mark student-mark">学</div>
        <div>
          <div class="brand-title">智慧大棚学生端</div>
          <div class="brand-subtitle">Cultiva · Student</div>
        </div>
      </div>

      <div class="nav-section-label">学习中心</div>
      <nav class="nav-list">
        <RouterLink class="nav-item" :to="{ name: 'student-dashboard' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </span>
          我的概览
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-tasks' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </span>
          我的任务
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-sensor' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-9 4 18 3-9h4"/></svg>
          </span>
          环境数据
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-submissions' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </span>
          我的作业
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-resources' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/></svg>
          </span>
          学习资源
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-experiments' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/></svg>
          </span>
          科学实验
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-pest-diagnoses' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </span>
          病虫害诊断
        </RouterLink>
        <RouterLink class="nav-item" :to="{ name: 'student-profile' }">
          <span class="nav-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </span>
          个人中心
        </RouterLink>
      </nav>

      <div class="sidebar-footer" v-if="auth.user">
        <div class="user-badge">
          <span class="user-avatar">
            <img v-if="auth.user.avatar_url" :src="auth.user.avatar_url" :alt="auth.user.display_name || auth.user.username" @error="onAvatarError" />
            <span :style="auth.user.avatar_url ? 'display: none' : ''">{{ (auth.user.display_name || auth.user.username).charAt(0).toUpperCase() }}</span>
          </span>
          {{ auth.user.display_name || auth.user.username }} · 学生
        </div>
        <button class="btn danger sm" style="margin-top: 8px; width: 100%" @click="handleLogout">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          退出登录
        </button>
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
          <RouterLink :to="{ name: 'student-profile' }" class="btn secondary sm topbar-profile-btn">
            <span class="topbar-avatar">
              <img v-if="auth.user?.avatar_url" :src="auth.user.avatar_url" :alt="auth.user?.display_name || auth.user?.username" @error="onAvatarError" />
              <span :style="auth.user?.avatar_url ? 'display: none' : ''">{{ (auth.user?.display_name || auth.user?.username || '?').charAt(0).toUpperCase() }}</span>
            </span>
            {{ auth.user?.display_name || auth.user?.username }}
          </RouterLink>
          <button class="theme-toggle" @click="toggle" type="button">
            <span class="theme-toggle-icon">
              <svg v-if="theme === 'dark'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
              <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            </span>
            {{ theme === 'dark' ? '浅色' : '深色' }}
            <span class="theme-toggle-track"></span>
          </button>
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
  'student-dashboard': '我的概览',
  'student-tasks': '我的任务',
  'student-sensor': '环境数据',
  'student-submissions': '我的作业',
  'student-resources': '学习资源',
  'student-experiments': '科学实验',
  'student-pest-diagnoses': '病虫害诊断',
  'student-profile': '个人中心',
}

const subtitleMap: Record<string, string> = {
  'student-dashboard': '查看小组设备状态和最新环境数据',
  'student-tasks': '完成老师布置的观察和实验任务',
  'student-sensor': '查看本组设备采集的环境数据',
  'student-submissions': '查看已提交的作业和老师的批阅反馈',
  'student-resources': '查看老师发布的课件、视频和文档资料',
  'student-experiments': '查看本组的科学实验项目，记录观察数据',
  'student-pest-diagnoses': '查看本组 ESP32-CAM 上传的植物诊断结果',
  'student-profile': '管理你的个人信息、头像和密码',
}

const title = computed(() => titleMap[String(route.name)] ?? '智慧大棚学生端')
const subtitle = computed(() => subtitleMap[String(route.name)] ?? '智慧大棚学习平台')

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}

function refreshPage() {
  window.location.reload()
}

function onAvatarError(event: Event) {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  const sibling = img.nextElementSibling as HTMLElement | null
  if (sibling) {
    sibling.style.display = 'inline'
  }
}
</script>

<style scoped>
/* 学生端 topbar 内的主题切换按钮：覆盖全局 .theme-toggle 的 sidebar 全宽样式 */
.theme-toggle {
  width: auto;
  margin-top: 0;
}
</style>
