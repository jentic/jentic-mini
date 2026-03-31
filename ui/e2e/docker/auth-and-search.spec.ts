import { test, expect } from '@playwright/test'

test.describe('Auth cycle', () => {
  test('logs in via UI and navigates to dashboard', async ({ page }) => {
    await page.goto('/')

    const loginButton = page.getByRole('button', { name: /log in/i })
    await loginButton.waitFor({ state: 'visible', timeout: 15_000 })

    await page.locator('#login-username').fill('admin')
    await page.locator('#login-password').fill('admin123')
    await loginButton.click()

    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 15_000 })
  })
})

test.describe('Search API', () => {
  test('searches via API key', async ({ request }) => {
    const loginRes = await request.post('/user/login', {
      data: { username: 'admin', password: 'admin123' },
    })
    expect(loginRes.ok()).toBeTruthy()

    const keyRes = await request.post('/default-api-key/generate')
    const keyBody = await keyRes.json()

    if (!keyBody.key) {
      test.skip(true, 'Key already claimed — skipping search test')
      return
    }

    const searchRes = await request.get('/search?q=test', {
      headers: { 'X-Jentic-API-Key': keyBody.key },
    })
    expect(searchRes.ok()).toBeTruthy()

    const results = await searchRes.json()
    expect(Array.isArray(results)).toBe(true)
  })
})
