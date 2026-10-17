import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  server: {
    port: 8081,
    // 临时外网分享（ngrok）
    allowedHosts: true,
    proxy: { '/api': 'http://localhost:9000' },
  },
})
