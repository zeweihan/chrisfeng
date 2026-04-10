import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3169,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:9169',
        changeOrigin: true,
      }
    }
  }
})
