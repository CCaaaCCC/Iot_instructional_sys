<template>
  <section class="stat-card" :class="color">
    <div v-if="$slots.icon" class="stat-icon" :class="color">
      <slot name="icon" />
    </div>
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ display }}</div>
    <div class="stat-footnote">{{ footnote }}</div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  label: string
  value: string | number
  footnote: string
  color?: 'green' | 'gold' | 'blue' | 'red'
  icon?: string
}>()

const display = ref<string | number>(typeof props.value === 'number' ? 0 : props.value)
let frame = 0

function animate(target: number) {
  cancelAnimationFrame(frame)
  const start = typeof display.value === 'number' ? display.value : 0
  const delta = target - start
  const startedAt = performance.now()
  const step = (now: number) => {
    const progress = Math.min((now - startedAt) / 600, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = Math.round(start + delta * eased)
    if (progress < 1) {
      frame = requestAnimationFrame(step)
    }
  }
  frame = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (value) => {
    if (typeof value === 'number') {
      animate(value)
    } else {
      display.value = value
    }
  },
  { immediate: true },
)
</script>
