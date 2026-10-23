<template>
  <div class="content-area">
    <div v-if="loading" class="content-area">
      <div v-for="i in 3" :key="i" class="skeleton card"></div>
    </div>
    <div v-else-if="error" class="msg-error">{{ error }}</div>
    <template v-else>
      <template v-if="groupedResources.length">
        <article
          v-for="group in groupedResources"
          :key="group.subject"
          class="content-card"
          style="margin-bottom: 18px"
        >
          <div class="card-header">
            <div>
              <h3 class="card-title">
                {{ group.subject === 'labor' ? '劳动课' : '科学课' }}
              </h3>
              <div class="card-subtitle">共 {{ group.items.length }} 份学习资料</div>
            </div>
          </div>
          <div class="task-list-vertical">
            <article v-for="r in group.items" :key="r.id" class="task-card">
              <div class="task-card-header">
                <div>
                  <h4 style="margin:0;font-size:16px">{{ r.title }}</h4>
                  <div class="task-badges" style="margin-top:6px">
                    <span class="badge info">
                      <span class="badge-dot"></span>
                      {{ typeLabel(r.resource_type) }}
                    </span>
                    <span class="badge muted">
                      <span class="badge-dot"></span>
                      {{ formatSize(r.file_size) }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="r.description" class="task-description">{{ r.description }}</div>
              <div class="task-card-footer">
                <button class="btn secondary sm" @click="previewItem = r">预览</button>
                <a
                  :href="r.file_url"
                  class="btn primary sm"
                  target="_blank"
                  rel="noopener"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  下载资料
                </a>
              </div>
            </article>
          </div>
        </article>
      </template>
      <EmptyState
        v-else
        icon="inbox"
        title="暂无学习资源"
        desc="老师发布课件或资料后，会出现在这里"
      />
    </template>

    <FilePreviewModal v-if="previewItem" :file="previewItem" @close="previewItem = null" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchMyResources } from '@/api/resources'
import FilePreviewModal from '@/components/FilePreviewModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import type { TeachingResource } from '@/types'

const resources = ref<TeachingResource[]>([])
const loading = ref(true)
const error = ref('')
const previewItem = ref<TeachingResource | null>(null)

const groupedResources = computed(() => {
  const map: Record<string, TeachingResource[]> = {}
  for (const r of resources.value) {
    const key = r.subject
    if (!map[key]) map[key] = []
    map[key].push(r)
  }
  return Object.entries(map).map(([subject, items]) => ({ subject, items }))
})

function typeLabel(t: string) {
  const map: Record<string, string> = {
    ppt: 'PPT',
    pptx: 'PPT',
    pdf: 'PDF',
    mp4: '视频',
    doc: 'Word',
    docx: 'Word',
    txt: '文本',
  }
  return map[t] || t
}

function formatSize(bytes: number | null) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(async () => {
  try {
    resources.value = await fetchMyResources()
  } catch {
    error.value = '加载学习资源失败。'
  } finally {
    loading.value = false
  }
})
</script>
