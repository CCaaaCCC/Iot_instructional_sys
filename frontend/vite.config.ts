import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
        ws: true,
      },
      '/avatars': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/courseware-files': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/resource-files': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/submission-files': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/pest-images': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'echarts-vendor': ['echarts'],
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
})
