<template>
  <section class="stat-card" :class="color">
    <div class="stat-icon" :class="color">
      <slot name="icon">{{ icon ? (iconMap[icon] ?? icon) : '' }}</slot>
    </div>
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-footnote">{{ footnote }}</div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  footnote: string
  color?: 'green' | 'gold' | 'blue' | 'red'
  icon?: string
}>()

const iconMap: Record<string, string> = {
  devices: '🖥',
  online: '🟢',
  rules: '⚙',
  tasks: '📋',
}
</script>
