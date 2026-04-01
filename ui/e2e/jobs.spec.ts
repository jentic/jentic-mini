import { test, expect } from '@playwright/test';
import {
	captureConsoleErrors,
	mockAuthenticatedUser,
	mockJobs,
	mockJobDetail,
	mockToolkits,
	navigateTo,
} from './fixtures';

test.describe('Jobs page', () => {
	test.beforeEach(async ({ page }) => {
		await mockAuthenticatedUser(page);
		await mockJobs(page);
		await mockToolkits(page);
	});

	test('renders without errors', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await page.goto('/');
		await navigateTo(page, '/jobs');
		await expect(page.getByRole('heading', { name: /background jobs/i })).toBeVisible();
		expect(errors).toHaveLength(0);
	});

	test('shows status filter pills', async ({ page }) => {
		await page.goto('/');
		await navigateTo(page, '/jobs');
		await expect(page.getByRole('button', { name: 'all' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'pending' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'running' })).toBeVisible();
	});

	test('shows empty state when no jobs', async ({ page }) => {
		await page.goto('/');
		await navigateTo(page, '/jobs');
		await expect(page.getByText(/no jobs found/i)).toBeVisible();
	});
});

test.describe('Job detail page', () => {
	test('renders job detail', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await mockAuthenticatedUser(page);
		await mockJobDetail(page, 'job-1');
		await mockToolkits(page);

		await page.goto('/');
		await navigateTo(page, '/jobs/job-1');
		await expect(page.getByText('job-1')).toBeVisible();
		await expect(page.getByText(/back to jobs/i)).toBeVisible();
		await expect(page.getByText(/summary/i).first()).toBeVisible();

		expect(errors).toHaveLength(0);
	});
});
