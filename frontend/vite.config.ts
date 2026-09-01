import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const apiTarget = process.env.LG_API_PROXY || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/health': { target: apiTarget, changeOrigin: true },
      '/graphs': { target: apiTarget, changeOrigin: true },
      '/threads': { target: apiTarget, changeOrigin: true },
      '/runs': { target: apiTarget, changeOrigin: true },
    },
  },
})
