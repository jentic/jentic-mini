import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: { outDir: '../src/static', emptyOutDir: true },
  server: {
    proxy: {
      '/api': 'http://localhost:8900',
      '/user': 'http://localhost:8900',
      '/search': 'http://localhost:8900',
      '/toolkits': 'http://localhost:8900',
      '/credentials': 'http://localhost:8900',
      '/traces': 'http://localhost:8900',
      '/jobs': 'http://localhost:8900',
      '/apis': 'http://localhost:8900',
      '/workflows': 'http://localhost:8900',
      '/catalog': 'http://localhost:8900',
      '/health': 'http://localhost:8900',
      '/import': 'http://localhost:8900',
      '/inspect': 'http://localhost:8900',
      '/notes': 'http://localhost:8900',
      '/default-api-key': 'http://localhost:8900'
    }
  }
})
