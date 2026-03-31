import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
export const SHARED_STATE_PATH = join(__dirname, '.docker-e2e-state.json')

test.describe('Setup flow', () => {
  test('creates admin account and generates API key', async ({ page, request }) => {
    const healthRes = await request.get('/health')
    const health = await healthRes.json()

    if (health.status === 'ok') {
      test.skip(true, 'Setup already completed — skipping setup flow')
      return
    }

    expect(health.status).toMatch(/setup_required|account_required/)

    await page.goto('/')
    await expect(page.getByText(/create admin account/i)).toBeVisible({ timeout: 15_000 })

    await page.getByLabel('Username').fill('admin')
    await page.getByLabel('Password').fill('admin123')
    await page.getByRole('button', { name: /create account/i }).click()

    await expect(page.getByText(/admin account created/i)).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: /generate agent api key/i }).click()
    await expect(page.getByText(/will not be shown again/i)).toBeVisible({ timeout: 15_000 })

    const keyText = await page.evaluate(() => {
      const all = document.body.innerText
      const match = all.match(/tk_[a-fA-F0-9]+/)
      return match ? match[0] : null
    })

    if (keyText) {
      fs.writeFileSync(SHARED_STATE_PATH, JSON.stringify({ apiKey: keyText }))
    }
  })
})
