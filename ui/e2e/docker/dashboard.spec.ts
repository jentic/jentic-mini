import { test, expect } from '@playwright/test';
import { captureConsoleErrors } from './helpers';

/**
 * Dashboard (real backend). The dashboard has no aggregate endpoint — it
 * composes the overview CLIENT-SIDE from four list endpoints (agents, events,
 * executions, apis). On a clean fixtures DB those all return `{data:[]}`, so
 * this asserts the page renders its overview shell and degrades empty sources
 * gracefully (each widget owns its own state) without console errors.
 *
 * Reuses the authenticated storageState from auth.setup.ts (see the `e2e`
 * project in playwright.docker.config.ts) — no per-spec login.
 */
test('dashboard renders its overview against an empty backend, console clean', async ({ page }) => {
	const errors = captureConsoleErrors(page);

	await page.goto('/app');

	// Landing header + primary nav are present.
	await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
	await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();

	// The composed overview cards mount even with no data. These headings are
	// static labels owned by the dashboard module (not data-dependent), so they
	// render against an empty DB.
	await expect(page.getByRole('heading', { name: 'Agents awaiting approval' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Needs attention' })).toBeVisible();

	// One failing/empty source must not spam the console with app errors.
	expect(errors, `unexpected console errors:\n${errors.join('\n')}`).toEqual([]);
});

test('dashboard quick actions navigate to their surfaces', async ({ page }) => {
	await page.goto('/app');
	await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

	// QuickActions links route into the module surfaces (real router, real guard).
	await page.getByRole('link', { name: 'Create toolkit' }).click();
	await expect(page).toHaveURL(/\/app\/toolkits\b/);
	await expect(page.getByRole('heading', { name: 'Toolkits' })).toBeVisible();
});
