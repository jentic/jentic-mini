import { test, expect } from '@playwright/test';
import {
	captureConsoleErrors,
	mockAuthenticatedUser,
	mockOAuthBrokers,
	mockToolkits,
	navigateTo,
} from './fixtures';

test.describe('OAuth Brokers page', () => {
	test.beforeEach(async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockOAuthBrokers(page);
		await mockToolkits(page);
	});

	test('renders without errors', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await page.goto('/');
		await navigateTo(page, '/oauth-brokers');
		await expect(page.getByRole('heading', { name: /oauth brokers/i })).toBeVisible();
		expect(errors).toHaveLength(0);
	});

	test('shows add broker button', async ({ page }) => {
		await page.goto('/');
		await navigateTo(page, '/oauth-brokers');
		await expect(page.getByRole('button', { name: /add broker/i }).first()).toBeVisible();
	});
});
