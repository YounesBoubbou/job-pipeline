import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on the home network too, so a phone on the same Wi-Fi can open the app
    host: true,
    port: 5173,
    // Fail instead of moving to another port, so the address start.ps1 prints is right
    strictPort: true,
    proxy: {
      // All /api/* requests are forwarded to the FastAPI backend, which stays on
      // this PC only: the phone talks to Vite, and Vite talks to the API
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
