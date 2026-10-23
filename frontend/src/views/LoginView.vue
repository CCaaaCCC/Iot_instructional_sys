<template>
  <div class="login-shell">
    <div class="vein-bg"></div>
    <div class="login-card">
      <section class="login-hero">
        <div class="brand">
          <div class="brand-mark">棚</div>
          <div>
            <div class="brand-title">智慧大棚</div>
            <div class="brand-subtitle">Cultiva · Field Journal</div>
          </div>
        </div>
        <h1>面向劳动课与科学课的<br />智慧大棚教学平台</h1>
        <div class="hero-rule"></div>
        <p>
          统一管理 ESP32 设备节点、传感器数据与自动规则；
          支持教师分组教学、课堂任务发布、学生作业提交与批阅，
          让每一株植物的生长都成为可记录、可追问的科学探索。
        </p>
        <div class="actions">
          <button type="button" class="badge success badge-button" title="点击填充演示账号" @click="fillAccount('admin', 'Admin123456')">
            <span class="badge-dot"></span> 管理员 · admin
          </button>
          <button type="button" class="badge warning badge-button" title="点击填充演示账号" @click="fillAccount('teacher', 'Teacher123456')">
            <span class="badge-dot"></span> 教师 · teacher
          </button>
          <button type="button" class="badge info badge-button" title="点击填充演示账号" @click="fillAccount('g1s1', 'Student123456')">
            <span class="badge-dot"></span> 学生 · g1s1
          </button>
        </div>
        <p class="login-account-hint">点击账号可自动填充</p>
      </section>

      <section class="login-panel">
        <h2>登录系统</h2>
        <p class="page-desc">使用你的账号进入教学管理平台</p>

        <form class="login-form" @submit.prevent="handleLogin">
          <label>
            <div class="form-label">用户名</div>
            <input v-model="form.username" class="input" placeholder="请输入用户名" autocomplete="username" />
          </label>
          <label>
            <div class="form-label">密码</div>
            <div class="password-field">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="input"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" /><path d="M1 1l22 22" /><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" /></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" /><circle cx="12" cy="12" r="3" /></svg>
              </button>
            </div>
          </label>
          <button ref="loginButton" :class="['btn', 'primary', { loading }]" :disabled="loading">
            登录
          </button>
        </form>

        <div v-if="error" :class="['msg-error', { shake: errorShake }]" @animationend="errorShake = false">
          {{ error }}
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const error = ref('')
const errorShake = ref(false)
const showPassword = ref(false)
const loginButton = ref<HTMLButtonElement | null>(null)

const form = reactive({
  username: 'admin',
  password: 'Admin123456',
})

function fillAccount(username: string, password: string) {
  form.username = username
  form.password = password
  error.value = ''
  nextTick(() => loginButton.value?.focus())
}

async function handleLogin() {
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    errorShake.value = true
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.username.trim(), form.password)
    const role = auth.user?.role
    if (role === 'student') {
      await router.push({ name: 'student-dashboard' })
      return
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch {
    error.value = '登录失败，请检查用户名和密码，或确认后端服务已启动。'
    errorShake.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const auto = route.query.auto
  if (auto === 'teacher') {
    fillAccount('teacher', 'Teacher123456')
    setTimeout(handleLogin, 300)
  } else if (auto === 'student') {
    fillAccount('g1s1', 'Student123456')
    setTimeout(handleLogin, 300)
  } else if (auto === '1' || auto === 'admin') {
    fillAccount('admin', 'Admin123456')
    setTimeout(handleLogin, 300)
  }
})
</script>
