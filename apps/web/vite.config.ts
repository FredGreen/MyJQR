import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8080,
    // 临时外网分享（ngrok）：允许任意 Host 访问 dev server
    allowedHosts: true,
    proxy: {
      // 一个域名同时提供管理后台：/admin/* 转发到 admin dev server（8081）
      '/admin': { target: 'http://localhost:8081', ws: true },
      '/api': 'http://localhost:9000',
    },
  },
})
