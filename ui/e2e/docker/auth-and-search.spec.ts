import { test, expect } from '@playwright/test'

test.describe('Auth cycle', () => {
  test('logs in, verifies session, navigates, and logs out', async ({ page }) => {
    await page.goto('/')

    const url = page.url()
    if (url.includes('/login')) {
      await page.getByLabel('Username').fill('admin')
      await page.getByLabel('Password').fill('admin123')
      await page.getByRole('button', { name: /log in/i }).click()
    }

    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 10_000 })

    const meRes = await page.request.get('/user/me')
    const me = await meRes.json()
    expect(me.logged_in).toBe(true)

    await page.getByRole('link', { name: /search/i }).first().click()
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible()
  })
})

test.describe('Search + inspect', () => {
  test('searches and receives results', async ({ page }) => {
    const keyRes = await page.request.post('/default-api-key/generate')
    const { key } = await keyRes.json()

    const searchRes = await page.request.get(`/search?q=test`, {
      headers: { 'X-Jentic-API-Key': key },
    })
    expect(searchRes.ok()).toBeTruthy()

    const results = await searchRes.json()
    expect(Array.isArray(results)).toBe(true)
  })
})
