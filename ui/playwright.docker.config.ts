import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: './e2e/docker',
	timeout: 30_000,
	retries: 1,
	workers: 1,
	use: {
		baseURL: 'http://localhost:8900',
		trace: 'on-first-retry',
	},
	// Spawn a second container at /foo for the prefix-mount spec. Playwright
	// keeps it alive for the test run and tears it down afterwards (--rm).
	// Locally, set reuseExistingServer to skip the spawn when the container
	// is already up; in CI we always start fresh.
	webServer: {
		command:
			'docker rm -f jentic-mini-prefix-e2e 2>/dev/null; docker run --rm --name jentic-mini-prefix-e2e -p 8901:8900 -e JENTIC_TELEMETRY=off -e JENTIC_ROOT_PATH=/foo jentic-mini:latest',
		url: 'http://localhost:8901/foo/health',
		timeout: 90_000,
		reuseExistingServer: !process.env.CI,
	},
	projects: [
		{ name: 'setup', testMatch: 'setup.spec.ts' },
		{
			name: 'e2e',
			testMatch: '*.spec.ts',
			testIgnore: ['setup.spec.ts', 'prefix-mount.spec.ts'],
			dependencies: ['setup'],
		},
		// The prefix-mount project hits the second container directly via absolute
		// URLs and runs its own setup, so it has no dependency on the main setup.
		{ name: 'prefix-mount', testMatch: 'prefix-mount.spec.ts' },
	],
	reporter: [['html', { open: 'never' }]],
});
