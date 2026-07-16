<template>
  <div class="notification-bell" ref="bellRef">
    <button class="bell-btn" @click="toggleDropdown" type="button" :aria-label="`通知（${unreadCount} 条未读）`">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
      <span v-if="unreadCount > 0" class="bell-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <div v-if="open" class="bell-dropdown">
      <div class="bell-dropdown-header">
        <span class="bell-dropdown-title">通知</span>
        <button v-if="unreadCount > 0" class="bell-mark-all" @click="handleMarkAllRead" type="button">全部已读</button>
      </div>
      <div class="bell-dropdown-body">
        <div v-if="loading" class="bell-empty">加载中...</div>
        <div v-else-if="notifications.length === 0" class="bell-empty">暂无通知</div>
        <div v-else>
          <button
            v-for="n in notifications"
            :key="n.id"
            class="bell-item"
            :class="{ unread: !n.is_read }"
            @click="handleClickNotification(n)"
            type="button"
          >
            <div class="bell-item-title">{{ n.title }}</div>
            <div class="bell-item-content">{{ n.content }}</div>
            <div class="bell-item-time">{{ formatTime(n.created_at) }}</div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { notificationsApi, type Notification } from '@/api/notifications'

const router = useRouter()
const open = ref(false)
const loading = ref(false)
const unreadCount = ref(0)
const notifications = ref<Notification[]>([])
const bellRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchUnreadCount() {
  try {
    const res = await notificationsApi.unreadCount()
    unreadCount.value = res.count
  } catch {
    // ignore
  }
}

async function fetchList() {
  loading.value = true
  try {
    notifications.value = await notificationsApi.list({ limit: 10 })
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  open.value = !open.value
  if (open.value) {
    fetchList()
  }
}

async function handleClickNotification(n: Notification) {
  if (!n.is_read) {
    try {
      await notificationsApi.markRead(n.id)
      n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch {
      // ignore
    }
  }
  open.value = false
  if (n.link) {
    router.push(n.link).catch(() => {
      // ignore navigation errors
    })
  }
}

async function handleMarkAllRead() {
  try {
    await notificationsApi.markAllRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch {
    // ignore
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  return d.toLocaleDateString('zh-CN')
}

function handleClickOutside(e: MouseEvent) {
  if (bellRef.value && !bellRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => {
  fetchUnreadCount()
  pollTimer = setInterval(fetchUnreadCount, 30000)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  document.removeEventListener('click', handleClickOutside)
})

// 暴露刷新方法供外部调用（如 WebSocket 收到 notification 事件时）
defineExpose({ refresh: fetchUnreadCount })
</script>

<style scoped>
.notification-bell {
  position: relative;
  display: inline-block;
}

.bell-btn {
  position: relative;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
  color: var(--text);
  display: inline-flex;
  align-items: center;
  transition: background 0.15s, border-color 0.15s;
}
.bell-btn:hover {
  background: var(--panel-hover);
  border-color: var(--primary);
}

.bell-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--danger, #e53935);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  line-height: 1;
}

.bell-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 340px;
  max-width: 90vw;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  box-shadow: var(--shadow);
  z-index: 1000;
  overflow: hidden;
}

.bell-dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
}
.bell-dropdown-title {
  font-weight: 600;
  color: var(--text);
}
.bell-mark-all {
  background: transparent;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}
.bell-mark-all:hover {
  background: var(--panel-hover);
}

.bell-dropdown-body {
  max-height: 380px;
  overflow-y: auto;
}

.bell-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.bell-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--line);
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.12s;
}
.bell-item:hover {
  background: var(--panel-hover);
}
.bell-item.unread {
  background: var(--primary-soft);
}
.bell-item.unread:hover {
  background: var(--primary-glow);
}

.bell-item-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  margin-bottom: 4px;
}
.bell-item-content {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.bell-item-time {
  font-size: 11px;
  color: var(--muted);
  opacity: 0.7;
}
</style>
