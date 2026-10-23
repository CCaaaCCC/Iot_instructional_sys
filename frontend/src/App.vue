<template>
  <router-view />
  <AppToast />
  <AppConfirm />
</template>

<script setup lang="ts">
import AppToast from '@/components/AppToast.vue'
import AppConfirm from '@/components/AppConfirm.vue'
</script>
