<template>
  <div :class="['empty-state-box', { compact }]">
    <div class="empty-state-art">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="icon === 'leaf'">
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </template>
        <template v-else-if="icon === 'inbox'">
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
          <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" />
        </template>
        <template v-else-if="icon === 'chart'">
          <path d="M3 3v18h18" />
          <path d="m7 15 4-4 3 3 5-6" />
        </template>
        <template v-else-if="icon === 'camera'">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </template>
        <template v-else-if="icon === 'flask'">
          <path d="M9 3h6" />
          <path d="M10 3v6.5L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9.5V3" />
          <path d="M7.5 15h9" />
        </template>
        <template v-else>
          <path d="M7 20h10" />
          <path d="M12 20v-8" />
          <path d="M12 12c0-4 3-7 7-7 0 4-3 7-7 7Z" />
          <path d="M12 14c0-3-2.5-5.5-5.5-5.5 0 3 2.5 5.5 5.5 5.5Z" />
        </template>
      </svg>
    </div>
    <p class="empty-state-title">{{ title }}</p>
    <p v-if="desc" class="empty-state-desc">{{ desc }}</p>
    <button v-if="actionText" class="btn secondary sm empty-state-action" type="button" @click="$emit('action')">
      {{ actionText }}
    </button>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    icon?: 'sprout' | 'leaf' | 'inbox' | 'chart' | 'camera' | 'flask'
    title: string
    desc?: string
    actionText?: string
    compact?: boolean
  }>(),
  { icon: 'sprout', desc: '', actionText: '', compact: false }
)

defineEmits<{ action: [] }>()
</script>
