import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev the Vite server (5173) proxies API + WebSocket traffic to the FastAPI backend (8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
