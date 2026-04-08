import { test, expect } from '@playwright/test';
import {
	captureConsoleErrors,
	mockAuthenticatedUser,
	mockOAuthBrokers,
	mockToolkits,
	navigateTo,
} from './fixtures';

test.describe('OAuth Brokers redirect', () => {
	test.beforeEach(async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockOAuthBrokers(page);
		await mockToolkits(page);
	});

	test('redirects /oauth-brokers to /credentials', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await page.goto('/');
		await navigateTo(page, '/oauth-brokers');
		await expect(page).toHaveURL(/\/credentials/);
		expect(errors).toHaveLength(0);
	});
});
