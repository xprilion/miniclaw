import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [preact()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/v1': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: '../web-built',
    emptyOutDir: true,
  }
})