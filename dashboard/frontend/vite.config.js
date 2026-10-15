import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the FastAPI backend so the frontend
      // doesn't need to include the full host in every request.
      '/run-agent': 'http://localhost:8000',
      '/approve': 'http://localhost:8000',
      '/reject': 'http://localhost:8000',
    }
  }
})
