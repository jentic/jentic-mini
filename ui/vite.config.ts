import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

function copyApiDocsAssets(): import('vite').Plugin {
  return {
    name: 'copy-api-docs-assets',
    closeBundle() {
      const outDir = resolve(__dirname, '../static')
      const nm = resolve(__dirname, 'node_modules')
      copyFileSync(resolve(nm, 'swagger-ui-dist/swagger-ui-bundle.js'), resolve(outDir, 'swagger-ui-bundle.js'))
      copyFileSync(resolve(nm, 'swagger-ui-dist/swagger-ui.css'), resolve(outDir, 'swagger-ui.css'))
      copyFileSync(resolve(nm, 'redoc/bundles/redoc.standalone.js'), resolve(outDir, 'redoc.standalone.js'))
    },
  }
}

export default defineConfig({
  plugins: [react(), copyApiDocsAssets()],
  base: '/',
  build: { outDir: '../static', emptyOutDir: true },
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
