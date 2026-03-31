import { test, expect } from '@playwright/test'
import {
  captureConsoleErrors,
  mockAuthenticatedUser,
  mockWorkflows,
  mockWorkflowDetail,
  mockToolkits,
  navigateTo,
} from './fixtures'

test.describe('Workflows page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
    await mockWorkflows(page)
    await mockToolkits(page)
  })

  test('renders without errors', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await page.goto('/')
    await navigateTo(page, '/workflows')
    await expect(page.getByRole('heading', { name: /workflows/i })).toBeVisible()
    expect(errors).toHaveLength(0)
  })

  test('shows empty state when no workflows', async ({ page }) => {
    await page.goto('/')
    await navigateTo(page, '/workflows')
    await expect(page.getByText(/no workflows registered/i)).toBeVisible()
  })
})

test.describe('Workflow detail page', () => {
  test('renders workflow detail with steps', async ({ page }) => {
    const errors = captureConsoleErrors(page)
    await mockAuthenticatedUser(page)
    await mockWorkflowDetail(page, 'test-workflow')
    await mockWorkflows(page)
    await mockToolkits(page)

    await page.goto('/')
    await navigateTo(page, '/workflows/test-workflow')
    await expect(page.getByRole('heading', { name: 'Test Workflow' })).toBeVisible()
    await expect(page.getByText(/back to workflows/i)).toBeVisible()
    await expect(page.getByText(/2 steps/i)).toBeVisible()

    expect(errors).toHaveLength(0)
  })
})
