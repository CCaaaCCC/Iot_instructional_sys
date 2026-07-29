<template>
  <section class="stat-card" :class="color">
    <div v-if="$slots.icon" class="stat-icon" :class="color">
      <slot name="icon" />
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
</script>
