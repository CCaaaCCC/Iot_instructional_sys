<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="file-preview-modal">
      <div class="file-preview-header">
        <h3>{{ file.title }}</h3>
        <button class="btn ghost sm" @click="$emit('close')">关闭</button>
      </div>
      <div class="file-preview-body">
        <!-- PDF：直接 iframe 预览 -->
        <iframe
          v-if="previewKind === 'pdf'"
          :src="file.preview_url || file.file_url"
          class="file-preview-iframe"
          frameborder="0"
        ></iframe>

        <!-- 视频 -->
        <video
          v-else-if="previewKind === 'video'"
          :src="file.file_url"
          controls
          class="file-preview-video"
        ></video>

        <!-- 文本 -->
        <pre v-else-if="previewKind === 'text'" class="file-preview-text">{{ textContent }}</pre>

        <!-- Office 文件有预览 PDF -->
        <iframe
          v-else-if="previewKind === 'office-pdf'"
          :src="file.preview_url!"
          class="file-preview-iframe"
          frameborder="0"
        ></iframe>

        <!-- Office 文件无预览 -->
        <div v-else class="file-preview-fallback">
          <div class="file-preview-fallback-icon">📄</div>
          <p>该文件格式暂不支持在线预览</p>
          <a :href="file.file_url" class="btn primary" target="_blank" rel="noopener">下载文件</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface PreviewableFile {
  title: string
  file_type?: string
  resource_type?: string
  file_url: string
  preview_url: string | null
}

const props = defineProps<{ file: PreviewableFile }>()
defineEmits<{ close: [] }>()

const fileType = computed(() => props.file.file_type || props.file.resource_type || '')

const previewKind = computed(() => {
  const ft = fileType.value.toLowerCase()
  // PDF（原文件就是 PDF，或 Office 文件有预览 PDF）
  if (ft === 'pdf') return 'pdf'
  if (ft === 'mp4' || ft === 'video') return 'video'
  if (ft === 'txt') return 'text'
  // PPT / DOC 类型
  if (['ppt', 'pptx', 'doc', 'docx'].includes(ft)) {
    return props.file.preview_url ? 'office-pdf' : 'fallback'
  }
  return 'fallback'
})

const textContent = ref('')

async function loadText() {
  if (previewKind.value !== 'text') return
  try {
    const resp = await fetch(props.file.file_url)
    textContent.value = await resp.text()
  } catch {
    textContent.value = '文本加载失败'
  }
}

watch(() => props.file.file_url, loadText, { immediate: true })
</script>

<style scoped>
.file-preview-modal {
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-xl);
  width: min(90vw, 1100px);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  animation: cardSlideUp 0.3s ease;
  overflow: hidden;
}

.file-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  flex-shrink: 0;
}

.file-preview-header h3 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.file-preview-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--bg-elevated);
}

.file-preview-iframe {
  width: 100%;
  height: 80vh;
  border: none;
}

.file-preview-video {
  max-width: 100%;
  max-height: 80vh;
}

.file-preview-text {
  width: 100%;
  height: 80vh;
  overflow: auto;
  padding: 20px;
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text);
  background: var(--panel);
}

.file-preview-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 60px 20px;
  text-align: center;
}

.file-preview-fallback-icon {
  font-size: 48px;
}

.file-preview-fallback p {
  color: var(--muted);
  margin: 0;
}
</style>
