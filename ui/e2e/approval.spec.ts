import { test, expect } from '@playwright/test'
import { captureConsoleErrors, mockAuthenticatedUser, mockApproval, mockToolkits, navigateTo } from './fixtures'

test.describe('Approval page', () => {
  test('renders access request details', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await mockAuthenticatedUser(page)
    await mockApproval(page, 'tk-1', 'req-1')
    await mockToolkits(page)

    await page.goto('/')
    await navigateTo(page, '/approve/tk-1/req-1')
    await expect(page.getByText(/access request/i)).toBeVisible()

    expect(errors).toHaveLength(0)
  })

  test('shows approve and deny buttons', async ({ page }) => {
    await mockAuthenticatedUser(page)
    await mockApproval(page, 'tk-1', 'req-1')
    await mockToolkits(page)

    await page.goto('/')
    await navigateTo(page, '/approve/tk-1/req-1')
    await expect(page.getByRole('button', { name: /approve/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /deny/i })).toBeVisible()
  })

  test('redirects to login when not authenticated', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await page.route('**/health', (route) => {
      if (route.request().resourceType() !== 'fetch' && route.request().resourceType() !== 'xhr')
        return route.continue()
      return route.fulfill({ json: { status: 'ok' } })
    })
    await page.route('**/user/me', (route) => {
      if (route.request().resourceType() !== 'fetch' && route.request().resourceType() !== 'xhr')
        return route.continue()
      return route.fulfill({ json: { logged_in: false } })
    })

    await page.goto('/')
    await page.waitForURL('**/login**')

    expect(errors).toHaveLength(0)
  })
})
