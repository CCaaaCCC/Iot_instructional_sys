<template>
  <!-- 悬浮按钮（登录后渲染） -->
  <button
    v-if="!isOpen && canUseAI"
    class="ai-fab"
    type="button"
    title="AI 助手"
    @click="openDrawer"
  >
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2a4 4 0 0 1 4 4v1h1a4 4 0 0 1 4 4v2a4 4 0 0 1-4 4h-1v1a4 4 0 0 1-4 4 4 4 0 0 1-4-4v-1H7a4 4 0 0 1-4-4v-2a4 4 0 0 1 4-4h1V6a4 4 0 0 1 4-4z"/>
      <circle cx="9" cy="11" r="1" fill="currentColor"/>
      <circle cx="15" cy="11" r="1" fill="currentColor"/>
    </svg>
    <span class="ai-fab-label">AI</span>
    <span v-if="quota" class="ai-fab-badge">{{ quota.remaining }}</span>
  </button>

  <!-- 右侧抽屉 -->
  <Teleport to="body">
    <Transition name="ai-drawer">
      <div v-if="isOpen" class="ai-drawer-root">
        <div class="ai-drawer-mask" @click="closeDrawer"></div>
        <aside class="ai-drawer-panel">
          <header class="ai-drawer-header">
            <div class="ai-session-bar">
              <select
                :value="currentSessionId ?? ''"
                class="select ai-session-select"
                @change="onSessionChange"
              >
                <option value="">+ 新对话</option>
                <option v-for="s in sessions" :key="s.id" :value="s.id">
                  {{ s.title }}
                </option>
              </select>
              <button class="btn sm secondary" type="button" title="新建对话" @click="newSession">+</button>
              <button
                v-if="currentSessionId !== null"
                class="btn sm danger"
                type="button"
                title="删除当前会话"
                @click="onDeleteSession"
              >删</button>
            </div>
            <button class="ai-drawer-close" type="button" @click="closeDrawer">×</button>
          </header>

          <div ref="messagesContainer" class="ai-messages">
            <div v-if="!messages.length && !streaming" class="ai-empty">
              <div class="ai-empty-icon">AI</div>
              <p class="ai-empty-title">{{ greeting }}</p>
              <p class="ai-empty-desc">{{ emptyHint }}</p>
              <div class="ai-suggestions">
                <button
                  v-for="q in suggestions"
                  :key="q"
                  class="ai-suggestion"
                  type="button"
                  @click="sendSuggestion(q)"
                >
                  {{ q }}
                </button>
              </div>
            </div>
            <AiMessage
              v-for="msg in messages"
              :key="msg.id"
              :role="msg.role"
              :content="msg.content"
              :model-used="msg.model_used"
            />
            <AiMessage
              v-if="streaming"
              role="assistant"
              :content="streamingContent"
              :streaming="true"
            />
            <div v-if="error" class="ai-error">{{ error }}</div>
          </div>

          <footer class="ai-drawer-footer">
            <div v-if="quota" class="ai-quota-tip">
              今日剩余 {{ quota.remaining }}/{{ quota.limit }}
            </div>
            <div class="ai-input-area">
              <textarea
                v-model="inputText"
                class="input ai-textarea"
                placeholder="输入问题，Enter 发送，Shift+Enter 换行"
                :disabled="streaming"
                rows="2"
                @keydown.enter.exact.prevent="sendMessage"
              ></textarea>
              <button
                v-if="!streaming"
                class="btn primary"
                type="button"
                :disabled="!inputText.trim()"
                @click="sendMessage"
              >发送</button>
              <button v-else class="btn danger" type="button" @click="stopGeneration">停止</button>
            </div>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAI } from '@/composables/useAI'
import { useConfirm } from '@/composables/useConfirm'
import AiMessage from './AiMessage.vue'

const auth = useAuthStore()
const {
  isOpen,
  sessions,
  currentSessionId,
  messages,
  streaming,
  streamingContent,
  quota,
  error,
  inputText,
  openDrawer,
  closeDrawer,
  newSession,
  switchSession,
  sendMessage,
  stopGeneration,
  deleteSession,
} = useAI()

const messagesContainer = ref<HTMLElement | null>(null)
const confirm = useConfirm()

const canUseAI = computed(() => !!auth.user)
const isStudent = computed(() => auth.user?.role === 'student')

const greeting = computed(() =>
  isStudent.value ? '你好，我是棚棚小助手' : '你好，我是 AI 教学助手'
)
const emptyHint = computed(() =>
  isStudent.value
    ? '大棚种植、传感器、科学实验、学习任务，都可以问我。'
    : '备课、任务设计、实验方案、学情分析，都可以问我。'
)
const suggestions = computed(() =>
  isStudent.value
    ? ['土壤湿度多少合适？', '番茄叶子发黄怎么办？', '帮我解释光合作用']
    : ['帮我设计一节观察课', '如何分析学生成绩趋势？', '推荐一个科学实验方案']
)

async function sendSuggestion(question: string) {
  if (streaming.value) return
  inputText.value = question
  await sendMessage()
}

function onSessionChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value
  const id = val ? Number(val) : null
  if (id === null) {
    newSession()
  } else {
    switchSession(id)
  }
}

async function onDeleteSession() {
  if (currentSessionId.value === null) return
  const ok = await confirm({
    title: '删除当前对话',
    message: '删除后，这段对话的历史消息将无法恢复。',
    confirmText: '删除',
    danger: true,
  })
  if (ok) {
    await deleteSession(currentSessionId.value)
  }
}

// 流式时自动滚动到底部
watch(
  [messages, streamingContent],
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
  { deep: true },
)
</script>

<style scoped>
/* 悬浮按钮 */
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 60px;
  height: 60px;
  border-radius: var(--radius-full);
  border: 1px solid var(--line-strong);
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: var(--on-primary);
  cursor: pointer;
  box-shadow: 0 8px 24px var(--primary-glow), 0 2px 8px rgba(20, 12, 4, 0.4);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.ai-fab:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow: 0 12px 32px var(--primary-glow), 0 4px 12px rgba(20, 12, 4, 0.5);
}

.ai-fab:active {
  transform: translateY(0) scale(0.98);
}

.ai-fab-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.ai-fab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: var(--radius-full);
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--bg);
}

/* 抽屉根容器 */
.ai-drawer-root {
  position: fixed;
  inset: 0;
  z-index: 1100;
  pointer-events: auto;
}

.ai-drawer-mask {
  position: absolute;
  inset: 0;
  background: rgba(10, 8, 5, 0.5);
  backdrop-filter: blur(2px);
}

.ai-drawer-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  border-left: 1px solid var(--line);
  box-shadow: var(--shadow-lg);
}

.ai-drawer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  background: var(--bg-soft);
}

.ai-session-bar {
  flex: 1;
  display: flex;
  gap: 6px;
  align-items: center;
}

.ai-session-select {
  flex: 1;
  font-size: 13px;
  padding: 6px 8px;
}

.ai-drawer-close {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-full);
  border: 1px solid var(--line);
  background: var(--btn-secondary-bg);
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ai-drawer-close:hover {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: var(--danger);
}

/* 消息列表 */
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px;
  background: var(--bg);
}

.ai-empty {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 36px 16px;
  line-height: 1.7;
}

.ai-empty-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 4px;
}

.ai-empty-desc {
  font-size: 12.5px;
  color: var(--muted);
  margin: 0 0 16px;
}

.ai-suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
}

.ai-suggestion {
  padding: 9px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--text-secondary);
  font-size: 12.5px;
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.ai-suggestion:hover {
  border-color: var(--primary-glow);
  background: var(--primary-soft);
  color: var(--text);
  transform: translateX(2px);
}

.ai-empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: var(--on-primary);
  box-shadow: 0 4px 16px var(--primary-glow);
}

.ai-error {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 12.5px;
  border: 1px solid var(--danger);
}

/* 底部输入区 */
.ai-drawer-footer {
  border-top: 1px solid var(--line);
  padding: 10px 14px 12px;
  background: var(--bg-soft);
}

.ai-quota-tip {
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-align: right;
}

.ai-input-area {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.ai-textarea {
  flex: 1;
  resize: none;
  font-size: 13px;
  line-height: 1.5;
  padding: 8px 10px;
  min-height: 40px;
  max-height: 120px;
}

/* 抽屉过渡动画 */
.ai-drawer-enter-active,
.ai-drawer-leave-active {
  transition: opacity var(--transition-fast);
}
.ai-drawer-enter-active .ai-drawer-panel,
.ai-drawer-leave-active .ai-drawer-panel {
  transition: transform var(--transition);
}
.ai-drawer-enter-from,
.ai-drawer-leave-to {
  opacity: 0;
}
.ai-drawer-enter-from .ai-drawer-panel,
.ai-drawer-leave-to .ai-drawer-panel {
  transform: translateX(100%);
}

/* 响应式：窄屏占满 */
@media (max-width: 540px) {
  .ai-drawer-panel {
    width: 100vw;
  }
  .ai-fab {
    right: 16px;
    bottom: 16px;
    width: 52px;
    height: 52px;
  }
}
</style>
