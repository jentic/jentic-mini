import { test, expect } from '@playwright/test';
import {
	captureConsoleErrors,
	mockNotLoggedIn,
	mockSetupRequired,
	mockAccountRequired,
	mockAuthenticatedUser,
	mockDashboard,
} from './fixtures';

test.describe('Auth — Login page', () => {
	test('renders login form when not authenticated', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await mockNotLoggedIn(page);

		await page.goto('/login');
		await expect(page.getByRole('button', { name: /log in/i })).toBeVisible();
		await expect(page.locator('input[type="text"]')).toBeVisible();
		await expect(page.locator('input[type="password"]')).toBeVisible();

		expect(errors).toHaveLength(0);
	});

	test('redirects to login when unauthenticated user visits protected route', async ({
		page,
	}) => {
		await mockNotLoggedIn(page);

		await page.goto('/');
		await page.waitForURL('**/login**');
		await expect(page.getByRole('button', { name: /log in/i })).toBeVisible();
	});

	test('redirects logged-in user away from login to dashboard', async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockDashboard(page);

		await page.goto('/login');
		await page.waitForURL('/');
		await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
	});
});

test.describe('Auth — Setup page', () => {
	test('renders setup page when setup required', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await mockSetupRequired(page);

		await page.goto('/setup');
		await expect(page.getByRole('heading', { name: /welcome to jentic mini/i })).toBeVisible();

		expect(errors).toHaveLength(0);
	});

	test('redirects to setup when health returns setup_required', async ({ page }) => {
		await mockSetupRequired(page);

		await page.goto('/');
		await page.waitForURL('**/setup');
		await expect(page.getByRole('heading', { name: /welcome to jentic mini/i })).toBeVisible();
	});

	test('redirects to setup when health returns account_required', async ({ page }) => {
		await mockAccountRequired(page);

		await page.goto('/');
		await page.waitForURL('**/setup');
	});

	test('redirects logged-in user away from setup to dashboard', async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockDashboard(page);

		await page.goto('/setup');
		await page.waitForURL('/');
	});
});
