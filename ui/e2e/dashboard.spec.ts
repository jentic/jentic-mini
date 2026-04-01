import { test, expect } from '@playwright/test';
import { captureConsoleErrors, mockAuthenticatedUser, mockDashboard } from './fixtures';

test.describe('Dashboard page', () => {
	test.beforeEach(async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockDashboard(page);
	});

	test('renders without errors', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await page.goto('/');
		await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
		expect(errors).toHaveLength(0);
	});

	test('shows stat cards and quick actions', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByText(/apis registered/i)).toBeVisible();
		await expect(page.getByText(/quick actions/i)).toBeVisible();
	});

	test('recent executions section visible', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByText(/recent executions/i)).toBeVisible();
	});
});
