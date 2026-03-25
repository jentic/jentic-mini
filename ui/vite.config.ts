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

// In Docker dev (compose.dev.yml) this is overridden to http://jentic-mini:8900
// so the Vite container can reach the API container by service name.
// When running Vite directly on the host, the default http://localhost:8900 applies.
const apiHost = process.env.VITE_API_HOST || 'http://localhost:8900'

export default defineConfig({
  plugins: [react(), copyApiDocsAssets()],
  base: '/',
  build: { outDir: '../static', emptyOutDir: true },
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/api':          apiHost,
      '/user':         apiHost,
      '/search':       apiHost,
      '/toolkits':     apiHost,
      '/credentials':  apiHost,
      '/traces':       apiHost,
      '/jobs':         apiHost,
      '/apis':         apiHost,
      '/workflows':    apiHost,
      '/catalog':      apiHost,
      '/health':       apiHost,
      '/import':       apiHost,
      '/inspect':      apiHost,
      '/notes':        apiHost,
      '/default-api-key': apiHost,
      '/oauth-brokers': apiHost,
      '/docs':         apiHost,
      '/openapi.json': apiHost,
    }
  }
})
