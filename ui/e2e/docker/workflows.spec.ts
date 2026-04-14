/**
 * E2E tests for workflow import and loading against real backend.
 *
 * Tests the full workflow lifecycle:
 * 1. Import a workflow via API
 * 2. Navigate to workflows page
 * 3. Verify workflow appears in list
 * 4. Click to view workflow detail
 * 5. Verify workflow detail loads without errors
 *
 * Regression test for pathlib.Path shadowing issue that caused 500 errors.
 */
import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { test, expect } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SHARED_STATE_PATH = join(__dirname, '.docker-e2e-state.json');

function loadSharedState(): { apiKey?: string; sessionCookie?: string } {
	try {
		return JSON.parse(fs.readFileSync(SHARED_STATE_PATH, 'utf-8'));
	} catch {
		return {};
	}
}

const TEST_WORKFLOW = {
	arazzo: '1.0.0',
	info: {
		title: 'E2E Test Workflow',
		version: '1.0.0',
		description: 'Workflow for E2E testing',
	},
	sourceDescriptions: [
		{
			name: 'test-api',
			type: 'openapi',
			url: 'https://api.example.com/openapi.json',
		},
	],
	workflows: [
		{
			workflowId: 'e2e-test-workflow',
			summary: 'E2E test workflow',
			description: 'A workflow used to test import and loading functionality',
			inputs: {
				type: 'object',
				properties: {
					query: {
						type: 'string',
						description: 'Search query',
					},
				},
			},
			steps: [
				{
					stepId: 'search',
					description: 'Search for items',
					operationId: 'test-api.searchItems',
					parameters: [
						{
							name: 'q',
							in: 'query',
							value: '$inputs.query',
						},
					],
				},
				{
					stepId: 'get-details',
					description: 'Get first result details',
					operationId: 'test-api.getItem',
				},
			],
		},
	],
};

test.describe('Workflow Loading (Real Backend)', () => {
	test('imports workflow via API and verifies it loads', async ({ request, page }) => {
		const { sessionCookie } = loadSharedState();
		expect(
			sessionCookie,
			'Shared state missing sessionCookie — setup spec must run first',
		).toBeTruthy();

		// Import workflow via POST /import
		const importRes = await request.post('/import', {
			headers: {
				Cookie: `jentic_session=${sessionCookie}`,
				'Content-Type': 'application/json',
			},
			data: {
				sources: [
					{
						type: 'inline',
						content: JSON.stringify(TEST_WORKFLOW),
						filename: 'e2e-test-workflow.arazzo.json',
					},
				],
			},
		});

		expect(importRes.ok(), `Import failed: ${await importRes.text()}`).toBeTruthy();
		const importResult = await importRes.json();
		expect(importResult.imported).toBeGreaterThan(0);

		// Navigate to workflows page
		await page.goto('/');
		await page.context().addCookies([
			{
				name: 'jentic_session',
				value: sessionCookie!,
				domain: 'localhost',
				path: '/',
			},
		]);
		await page.goto('/workflows');

		// Wait for workflows page to load
		await expect(page.getByRole('heading', { name: /workflows/i })).toBeVisible({
			timeout: 10_000,
		});

		// Verify our workflow appears in the list
		const workflowCard = page.getByText('E2E Test Workflow');
		await expect(workflowCard).toBeVisible({ timeout: 5_000 });

		// Click on the workflow to view details
		await workflowCard.click();

		// Verify workflow detail page loads without errors
		await expect(page.getByText('E2E Test Workflow')).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText(/2 steps/i)).toBeVisible();
		await expect(page.getByText(/search/i)).toBeVisible();
		await expect(page.getByText(/get-details/i)).toBeVisible();

		// Verify no console errors (regression test for pathlib.Path shadowing)
		const errors: string[] = [];
		page.on('console', (msg) => {
			if (msg.type() === 'error') {
				errors.push(msg.text());
			}
		});

		// Reload the page to trigger any loading errors
		await page.reload();
		await expect(page.getByText('E2E Test Workflow')).toBeVisible({ timeout: 10_000 });

		// Should have no console errors
		expect(errors, `Console errors detected: ${errors.join(', ')}`).toHaveLength(0);
	});

	test('loads workflow via inspect API endpoint', async ({ request }) => {
		const { sessionCookie } = loadSharedState();
		expect(sessionCookie).toBeTruthy();

		// First ensure workflow is imported (idempotent)
		await request.post('/import', {
			headers: {
				Cookie: `jentic_session=${sessionCookie}`,
				'Content-Type': 'application/json',
			},
			data: {
				sources: [
					{
						type: 'inline',
						content: JSON.stringify(TEST_WORKFLOW),
						filename: 'e2e-test-workflow.arazzo.json',
					},
				],
			},
		});

		// Get the public hostname from health endpoint
		const healthRes = await request.get('/health');
		expect(healthRes.ok()).toBeTruthy();

		// Load workflow via GET /workflows/{slug}
		const workflowRes = await request.get('/workflows/e2e-test-workflow', {
			headers: { Cookie: `jentic_session=${sessionCookie}` },
		});

		expect(workflowRes.ok(), `GET /workflows failed: ${await workflowRes.text()}`).toBeTruthy();
		const workflow = await workflowRes.json();
		expect(workflow.slug).toBe('e2e-test-workflow');
		expect(workflow.name).toBe('E2E Test Workflow');
		expect(workflow.steps).toHaveLength(2);
		expect(workflow.source).toBe('local');
	});

	test('workflow list API returns imported workflows', async ({ request }) => {
		const { sessionCookie } = loadSharedState();
		expect(sessionCookie).toBeTruthy();

		// Import workflow
		await request.post('/import', {
			headers: {
				Cookie: `jentic_session=${sessionCookie}`,
				'Content-Type': 'application/json',
			},
			data: {
				sources: [
					{
						type: 'inline',
						content: JSON.stringify(TEST_WORKFLOW),
						filename: 'e2e-test-workflow.arazzo.json',
					},
				],
			},
		});

		// List workflows
		const listRes = await request.get('/workflows', {
			headers: { Cookie: `jentic_session=${sessionCookie}` },
		});

		expect(listRes.ok(), `GET /workflows failed: ${await listRes.text()}`).toBeTruthy();
		const workflows = await listRes.json();
		expect(Array.isArray(workflows)).toBe(true);
		expect(workflows.length).toBeGreaterThan(0);

		// Find our test workflow
		const testWorkflow = workflows.find((w: any) => w.slug === 'e2e-test-workflow');
		expect(testWorkflow).toBeTruthy();
		expect(testWorkflow.name).toBe('E2E Test Workflow');
		expect(testWorkflow.steps_count).toBe(2);
	});
});
