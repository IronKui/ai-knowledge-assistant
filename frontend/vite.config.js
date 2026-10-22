import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 监听 0.0.0.0，而不是仅 127.0.0.1：否则手机 / 隧道 / 局域网都连不进来
    host: true,
    port: 5173,
    // 前端只请求同源的 /api/*，由这里转发到后端，避免把 localhost 写死在代码里
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
