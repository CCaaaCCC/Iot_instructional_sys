<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="confirmState.open"
        class="modal-overlay confirm-overlay"
        role="presentation"
        @click.self="onOverlayClick"
      >
        <div class="modal-card confirm-card" role="dialog" aria-modal="true" :aria-label="confirmState.options.title">
          <div :class="['confirm-icon', { danger: confirmState.options.danger }]">
            <svg v-if="confirmState.options.danger" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4" /><path d="M12 17h.01" /></svg>
            <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 7.5h.01" /></svg>
          </div>
          <h3 class="confirm-title">{{ confirmState.options.title }}</h3>
          <p v-if="confirmState.options.message" class="confirm-message">{{ confirmState.options.message }}</p>
          <div class="modal-footer confirm-footer">
            <button class="btn secondary" type="button" @click="answer(false)">
              {{ confirmState.options.cancelText || '取消' }}
            </button>
            <button
              :class="['btn', confirmState.options.danger ? 'danger' : 'primary']"
              type="button"
              @click="answer(true)"
            >
              {{ confirmState.options.confirmText || '确定' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { confirmState, resolveConfirm } from '@/composables/useConfirm'

function answer(value: boolean) {
  resolveConfirm(value)
}

function onOverlayClick() {
  // 危险操作不允许点遮罩关闭，避免误触
  if (!confirmState.options.danger) {
    answer(false)
  }
}

function onKeydown(event: KeyboardEvent) {
  if (!confirmState.open) return
  if (event.key === 'Escape') {
    answer(false)
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>
