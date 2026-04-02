import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: './e2e',
	testIgnore: '**/docker/**',
	fullyParallel: true,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : '50%',
	reporter: [['html', { open: 'never' }]],
	use: {
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
	},
	webServer: {
		command: 'npm run dev',
		url: 'http://localhost:5173',
		reuseExistingServer: !process.env.CI,
		timeout: 30000,
	},
});
