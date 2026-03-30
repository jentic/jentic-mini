import { test, expect } from '@playwright/test'
import { captureConsoleErrors, mockAuthenticatedUser, mockSearch, mockToolkits, navigateTo } from './fixtures'

test.describe('Search page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
    await mockSearch(page)
    await mockToolkits(page)
  })

  test('renders without errors', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await page.goto('/')
    await navigateTo(page, '/search')
    await expect(page.getByRole('heading', { name: /search/i })).toBeVisible()
    expect(errors).toHaveLength(0)
  })

  test('shows search input and example queries', async ({ page }) => {
    await page.goto('/')
    await navigateTo(page, '/search')
    await expect(page.getByPlaceholder(/send an email/i)).toBeVisible()
  })
})
