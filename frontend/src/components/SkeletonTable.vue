<template>
  <div class="skeleton-table" aria-hidden="true">
    <div class="skeleton-table-head" :style="gridStyle">
      <span v-for="c in cols" :key="`h-${c}`" class="skeleton text" />
    </div>
    <div v-for="r in rows" :key="`r-${r}`" class="skeleton-table-row" :style="gridStyle">
      <span v-for="c in cols" :key="`c-${r}-${c}`" class="skeleton text" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ rows?: number; cols?: number }>(), { rows: 5, cols: 4 })

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${props.cols}, minmax(0, 1fr))`,
}))
</script>
