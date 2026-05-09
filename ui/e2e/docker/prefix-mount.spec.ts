import { test, expect } from '@playwright/test';

// Hits the prefix container started by the webServer block in
// playwright.docker.config.ts. Uses absolute URLs so the spec is unaffected
// by the default baseURL (which points at the unprefixed main container).
const PREFIX_BASE = 'http://localhost:8901/foo';
const ADMIN_USER = 'admin';
const ADMIN_PASS = 'admin123';

test.describe('Reverse-proxy prefix mount', () => {
	test('serves the SPA shell with a prefixed <base href>', async ({ request }) => {
		const res = await request.get(`${PREFIX_BASE}/`, {
			headers: { Accept: 'text/html' },
		});
		expect(res.ok()).toBeTruthy();
		const body = await res.text();
		expect(body).toContain('<base href="/foo/"');
	});

	test('navigates to credentials and survives a reload', async ({ page }) => {
		// 1. Bootstrap auth state — fresh container needs admin creation;
		//    a reused container needs login. Both paths leave us logged in.
		await page.goto(`${PREFIX_BASE}/`);

		const setupVisible = await page
			.getByText(/create admin account/i)
			.isVisible({ timeout: 5_000 })
			.catch(() => false);

		if (setupVisible) {
			await page.getByLabel('Username').fill(ADMIN_USER);
			await page.getByRole('textbox', { name: 'Password' }).fill(ADMIN_PASS);
			await page.getByRole('button', { name: /create account/i }).click();
			await expect(page.getByText(/setup complete/i)).toBeVisible({ timeout: 30_000 });
			// Continue from setup wizard's completion state to the dashboard.
			await page.goto(`${PREFIX_BASE}/`);
		} else {
			const loginVisible = await page
				.getByRole('button', { name: /^log in$/i })
				.isVisible({ timeout: 5_000 })
				.catch(() => false);
			if (loginVisible) {
				await page.getByLabel('Username').fill(ADMIN_USER);
				await page.getByRole('textbox', { name: 'Password' }).fill(ADMIN_PASS);
				await page.getByRole('button', { name: /^log in$/i }).click();
			}
		}

		// 2. Click the Credentials nav link — proves React Router's basename
		//    is reading the backend-injected <base href>.
		await page
			.getByRole('link', { name: /credentials/i })
			.first()
			.click();
		await expect(page).toHaveURL(`${PREFIX_BASE}/credentials`);
		await expect(page.getByRole('heading', { name: /credentials/i })).toBeVisible({
			timeout: 15_000,
		});

		// 3. Cold-boot deep-link path — reloading must keep the URL and re-render.
		await page.reload();
		await expect(page).toHaveURL(`${PREFIX_BASE}/credentials`);
		await expect(page.getByRole('heading', { name: /credentials/i })).toBeVisible({
			timeout: 15_000,
		});
	});
});
