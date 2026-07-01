import { defineConfig } from '@playwright/test';

/**
 * Mocked e2e config. Boots the Vite dev server with MSW enabled
 * (`VITE_ENABLE_MSW=1`), so specs run against mock data with no backend — fast,
 * deterministic, and CI-friendly. For tests against a real backend, see
 * playwright.docker.config.ts.
 */
export default defineConfig({
	testDir: './e2e',
	testIgnore: '**/docker/**',
	fullyParallel: true,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : '50%',
	reporter: [['html', { open: 'never' }]],
	use: {
		// The SPA is served under `/app/` (Vite `base`), so the bare host root
		// 404s in dev. Point baseURL at the mount; specs `goto('/app/...')`.
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
	},
	webServer: {
		command: 'VITE_ENABLE_MSW=1 npm run dev',
		// Vite serves the SPA under `base: '/app/'`; the readiness probe must hit
		// the mount (the bare root 404s) or Playwright never sees the server up.
		url: 'http://localhost:5173/app/',
		reuseExistingServer: !process.env.CI,
		timeout: 60_000,
	},
});
