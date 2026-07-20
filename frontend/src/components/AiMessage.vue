<template>
  <div class="ai-msg" :class="role">
    <div class="ai-msg-avatar" :class="{ user: role === 'user' }">
      {{ role === 'user' ? '我' : 'AI' }}
    </div>
    <div class="ai-msg-bubble">
      <div
        v-if="role === 'assistant'"
        class="ai-msg-content markdown-body"
        v-html="rendered"
      ></div>
      <div v-else class="ai-msg-content">{{ content }}</div>
      <span v-if="modelLabel && role === 'assistant'" class="ai-msg-model-tag">{{ modelLabel }}</span>
      <span v-if="streaming" class="ai-msg-cursor"></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{
  role: 'user' | 'assistant' | 'system'
  content: string
  streaming?: boolean
  modelUsed?: string | null
}>()

const modelLabel = computed(() => {
  if (!props.modelUsed) return null
  return props.modelUsed.includes('reasoner') ? '深度思考' : 'chat'
})

const rendered = computed(() => {
  // marked 12.x 默认同步解析；TS 类型可能给 string | Promise<string>，断言为 string
  const html = marked.parse(props.content || '') as string
  return DOMPurify.sanitize(html)
})
</script>

<style scoped>
.ai-msg {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.ai-msg.user {
  flex-direction: row-reverse;
}

.ai-msg-avatar {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: var(--on-primary);
  box-shadow: 0 2px 8px var(--primary-glow);
}

.ai-msg-avatar.user {
  background: linear-gradient(135deg, var(--accent), var(--terracotta));
  box-shadow: 0 2px 8px var(--terracotta-soft);
}

.ai-msg-bubble {
  position: relative;
  max-width: 80%;
  padding: 10px 14px;
  border-radius: var(--radius);
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  color: var(--text);
  font-size: 13.5px;
  line-height: 1.6;
  word-wrap: break-word;
  word-break: break-word;
}

.ai-msg.user .ai-msg-bubble {
  background: var(--primary-soft);
  border-color: var(--primary-glow);
}

.ai-msg-content :deep(p) {
  margin: 0 0 8px;
}
.ai-msg-content :deep(p:last-child) {
  margin-bottom: 0;
}
.ai-msg-content :deep(pre) {
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 10px;
  overflow-x: auto;
  margin: 6px 0;
  font-family: var(--font-mono);
  font-size: 12px;
}
.ai-msg-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--input-bg);
  padding: 1px 4px;
  border-radius: 4px;
}
.ai-msg-content :deep(pre code) {
  background: transparent;
  padding: 0;
}
.ai-msg-content :deep(ul),
.ai-msg-content :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.ai-msg-content :deep(li) {
  margin: 2px 0;
}
.ai-msg-content :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 12.5px;
}
.ai-msg-content :deep(th),
.ai-msg-content :deep(td) {
  border: 1px solid var(--line);
  padding: 4px 8px;
}
.ai-msg-content :deep(a) {
  color: var(--primary);
  text-decoration: underline;
}

/* 流式光标 */
.ai-msg-cursor {
  display: inline-block;
  width: 7px;
  height: 14px;
  margin-left: 2px;
  background: var(--primary);
  vertical-align: text-bottom;
  animation: ai-blink 1s steps(2) infinite;
}

/* 模型标签 */
.ai-msg-model-tag {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  border: 1px solid var(--primary-glow);
}

@keyframes ai-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
