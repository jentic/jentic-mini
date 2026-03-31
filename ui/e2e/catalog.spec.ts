import { test, expect } from '@playwright/test'
import { captureConsoleErrors, mockAuthenticatedUser, mockCatalog, mockToolkits, navigateTo } from './fixtures'

test.describe('API Catalog page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
    await mockCatalog(page)
    await mockToolkits(page)
  })

  test('renders without errors', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await page.goto('/')
    await navigateTo(page, '/catalog')
    await expect(page.getByRole('heading', { name: /api catalog/i })).toBeVisible()
    expect(errors).toHaveLength(0)
  })

  test('shows tabs and filter input', async ({ page }) => {
    await page.goto('/')
    await navigateTo(page, '/catalog')
    await expect(page.getByRole('button', { name: 'Your APIs' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Public Catalog' })).toBeVisible()
    await expect(page.getByPlaceholder(/filter/i)).toBeVisible()
  })
})
