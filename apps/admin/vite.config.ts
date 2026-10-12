import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  server: {
    port: 8081,
    proxy: { '/api': 'http://localhost:9000' },
  },
})
