import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { test, expect } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
export const SHARED_STATE_PATH = join(__dirname, '.docker-e2e-state.json');

test.describe('Setup flow', () => {
	test('creates admin account and stores toolkit key for downstream docker e2e', async ({
		page,
	}) => {
		const healthRes = await page.request.get('/health');
		const health = await healthRes.json();

		if (health.status === 'ok' && fs.existsSync(SHARED_STATE_PATH)) {
			test.skip(true, 'Setup already completed — shared state exists');
			return;
		}

		expect(health.status).toBe('setup_required');

		await page.goto('/');
		await expect(page.getByText(/create admin account/i)).toBeVisible({ timeout: 15_000 });

		await page.getByLabel('Username').fill('admin');
		await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
		await page.getByRole('button', { name: /create account/i }).click();

		await expect(page.getByText(/setup complete/i)).toBeVisible({ timeout: 30_000 });

		const keyRes = await page.request.post('/toolkits/default/keys', {
			data: { label: 'docker-e2e' },
		});
		expect(keyRes.ok(), await keyRes.text()).toBeTruthy();
		const keyBody = await keyRes.json();
		expect(keyBody.key).toMatch(/^tk_/);

		fs.writeFileSync(SHARED_STATE_PATH, JSON.stringify({ apiKey: keyBody.key }));
	});
});
