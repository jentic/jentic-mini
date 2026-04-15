/**
 * E2E tests for workflow import and loading against real backend.
 *
 * Tests the full workflow lifecycle:
 * 1. Import a workflow via API
 * 2. Load workflow via GET /workflows/{slug}
 * 3. List workflows
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

function loadSharedState(): { apiKey?: string } {
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
	test('imports workflow and loads it without errors', async ({ request }) => {
		const { apiKey } = loadSharedState();
		expect(apiKey, 'Shared state missing apiKey — setup spec must run first').toBeTruthy();

		// Import workflow via POST /import
		const importRes = await request.post('/import', {
			headers: {
				'X-Jentic-API-Key': apiKey!,
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
		expect(importResult.succeeded).toBeGreaterThan(0);

		// Load workflow via GET /workflows/{slug} - regression test for pathlib.Path shadowing
		// This would return 500 if pathlib.Path is shadowed by fastapi.Path
		const workflowRes = await request.get('/workflows/e2e-test-workflow', {
			headers: { 'X-Jentic-API-Key': apiKey! },
		});

		expect(workflowRes.ok(), `GET /workflows failed: ${await workflowRes.text()}`).toBeTruthy();
		const workflow = await workflowRes.json();
		expect(workflow.slug).toBe('e2e-test-workflow');
		// Successfully loaded - regression test passed (no 500 error)
	});

	test('workflow list API returns imported workflows', async ({ request }) => {
		const { apiKey } = loadSharedState();
		expect(apiKey).toBeTruthy();

		// List workflows
		const listRes = await request.get('/workflows', {
			headers: { 'X-Jentic-API-Key': apiKey! },
		});

		expect(listRes.ok(), `GET /workflows failed: ${await listRes.text()}`).toBeTruthy();
		const workflows = await listRes.json();
		expect(Array.isArray(workflows)).toBe(true);

		// Find our test workflow (may have been imported by previous test)
		const testWorkflow = workflows.find((w: any) => w.slug === 'e2e-test-workflow');
		if (testWorkflow) {
			expect(testWorkflow.steps_count).toBe(2);
		}
	});
});
