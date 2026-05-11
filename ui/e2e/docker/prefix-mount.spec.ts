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

	test('no failed XHR during initial SPA render at the prefix', async ({ page }) => {
		// Regression guard for #365: SPA-initiated fetches (React Query,
		// hand-rolled raw fetch) used to issue absolute paths like /health
		// instead of /foo/health, which 404 under a path-prefix mount because
		// absolute paths bypass <base href> per the HTML spec.
		//
		// Listen for every response while the SPA cold-boots. Any 4xx/5xx on a
		// same-origin XHR / fetch is a regression. We exclude 401s on /user/me
		// — that endpoint is intentionally returned as a logged-out signal
		// before auth, not an error.
		// Capture same-origin fetch/XHR failures. Intentionally NOT filtered to
		// PREFIX_BASE: the bug this test guards against is the SPA issuing requests
		// WITHOUT the prefix (e.g. /health instead of /foo/health), so those
		// failing URLs would NOT start with PREFIX_BASE and would be silently
		// dropped by such a filter. Filter to same origin only to exclude CDN.
		const origin = new URL(PREFIX_BASE).origin;
		const failures: { url: string; status: number }[] = [];
		page.on('response', (resp) => {
			const url = resp.url();
			const status = resp.status();
			if (!url.startsWith(origin)) return;
			if (status < 400) return;
			const req = resp.request();
			if (!['fetch', 'xhr'].includes(req.resourceType())) return;
			// /user/me intentionally 401s when logged out (used as a probe).
			if (status === 401 && url.endsWith('/user/me')) return;
			failures.push({ url, status });
		});

		await page.goto(`${PREFIX_BASE}/`);
		// Wait for any setup/login UI to settle — that's the end of the
		// initial render's XHR storm.
		await page.waitForLoadState('networkidle');

		expect(failures, `unexpected failed XHRs: ${JSON.stringify(failures)}`).toEqual([]);
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
