import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SHARED_STATE_PATH = join(__dirname, '.docker-e2e-state.json')

function loadSharedState(): { apiKey?: string } {
  try {
    return JSON.parse(fs.readFileSync(SHARED_STATE_PATH, 'utf-8'))
  } catch {
    return {}
  }
}

test.describe('Auth cycle', () => {
  test('logs in via UI and navigates to dashboard', async ({ page }) => {
    await page.goto('/')

    const loginButton = page.getByRole('button', { name: /log in/i })
    await loginButton.waitFor({ state: 'visible', timeout: 15_000 })

    await page.getByLabel('Username').fill('admin')
    await page.getByLabel('Password').fill('admin123')
    await loginButton.click()

    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 15_000 })
  })
})

test.describe('Search API', () => {
  test('searches using the key generated during setup', async ({ request }) => {
    const { apiKey } = loadSharedState()
    expect(apiKey, 'Shared state file missing or has no apiKey — setup spec must run first').toBeTruthy()

    const searchRes = await request.get('/search?q=test', {
      headers: { 'X-Jentic-API-Key': apiKey! },
    })
    expect(searchRes.ok()).toBeTruthy()

    const results = await searchRes.json()
    expect(Array.isArray(results)).toBe(true)
  })
})
