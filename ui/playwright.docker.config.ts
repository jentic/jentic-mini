import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e/docker',
  timeout: 30_000,
  retries: 1,
  workers: 1,
  use: {
    baseURL: 'http://localhost:8900',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'setup', testMatch: 'setup.spec.ts' },
    { name: 'e2e', testMatch: '*.spec.ts', testIgnore: 'setup.spec.ts', dependencies: ['setup'] },
  ],
  reporter: [['html', { open: 'never' }]],
})
