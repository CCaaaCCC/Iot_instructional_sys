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
        <p>
          统一管理 ESP32 设备节点、传感器数据与自动规则；
          支持教师分组教学、课堂任务发布、学生作业提交与批阅，
          让每一株植物的生长都成为可记录、可追问的科学探索。
        </p>
        <div class="actions">
          <span class="badge success"><span class="badge-dot"></span> 管理员 · admin / Admin123456</span>
          <span class="badge warning"><span class="badge-dot"></span> 教师 · teacher / Teacher123456</span>
          <span class="badge info"><span class="badge-dot"></span> 学生 · g1s1 / Student123456</span>
        </div>
      </section>

      <section class="login-panel">
        <h2>登录系统</h2>
        <p class="page-desc">使用 JWT 凭证进入教学管理后台</p>

        <form class="login-form" @submit.prevent="handleLogin">
          <label>
            <div class="form-label">用户名</div>
            <input v-model="form.username" class="input" placeholder="请输入用户名" autocomplete="username" />
          </label>
          <label>
            <div class="form-label">密码</div>
            <input v-model="form.password" type="password" class="input" placeholder="请输入密码" autocomplete="current-password" />
          </label>
          <button class="btn primary" :disabled="loading">
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>

        <div v-if="error" class="msg-error">{{ error }}</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const error = ref('')

const form = reactive({
  username: 'admin',
  password: 'Admin123456',
})

async function handleLogin() {
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
  } catch (err) {
    error.value = '登录失败，请检查用户名和密码，或确认后端服务已启动。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const auto = route.query.auto
  if (auto === 'teacher') {
    form.username = 'teacher'
    form.password = 'Teacher123456'
    setTimeout(handleLogin, 300)
  } else if (auto === 'student') {
    form.username = 'g1s1'
    form.password = 'Student123456'
    setTimeout(handleLogin, 300)
  } else if (auto === '1' || auto === 'admin') {
    form.username = 'admin'
    form.password = 'Admin123456'
    setTimeout(handleLogin, 300)
  }
})
</script>
