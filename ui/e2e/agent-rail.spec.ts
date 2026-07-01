import { test, expect, type Page } from '@playwright/test';

/**
 * Agent Rail (mocked) e2e. The rail is a shell-mounted surface present on every
 * authenticated page at `xl+` (≥1280px), backed by the real `/events` feed
 * (served by MSW in Mode A). This spec logs in, asserts the rail mounts with a
 * live event feed, exercises collapse/expand persistence, and confirms the rail
 * is hidden below `xl`.
 */

function captureConsoleErrors(page: Page): string[] {
	const errors: string[] = [];
	page.on('console', (msg) => {
		if (msg.type() !== 'error') return;
		const text = msg.text();
		if (text.includes('Failed to load resource')) return;
		if (text.includes('net::ERR_')) return;
		errors.push(text);
	});
	return errors;
}

async function login(page: Page) {
	await page.goto('/app/');
	await expect(page.getByRole('heading', { name: 'Sign in to Jentic One' })).toBeVisible();
	await page.getByLabel('Email').fill('admin@local');
	await page.getByRole('textbox', { name: 'Password' }).fill('password');
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
}

test.describe('Agent Rail — shell-mounted live event feed', () => {
	test('mounts at xl with a live feed; collapse persists', async ({ page }) => {
		const errors = captureConsoleErrors(page);
		await page.setViewportSize({ width: 1440, height: 900 });
		await login(page);

		const rail = page.getByRole('complementary', { name: /Agent rail/i });
		await expect(rail).toBeVisible();
		await expect(rail.getByText('Agent rail')).toBeVisible();
		// A seeded backlog event renders in the feed.
		await expect(rail.getByText(/Execution failed: slack\.postMessage/i)).toBeVisible();

		// Collapse → the expand affordance appears and the header title is gone.
		await rail.getByRole('button', { name: 'Collapse agent rail' }).click();
		await expect(page.getByRole('button', { name: 'Expand agent rail' })).toBeVisible();
		await expect(rail.getByText('Agent rail')).toBeHidden();

		// Collapse survives a reload (persisted to localStorage).
		await page.reload();
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Expand agent rail' })).toBeVisible();

		// Expand again.
		await page.getByRole('button', { name: 'Expand agent rail' }).click();
		await expect(rail.getByText('Agent rail')).toBeVisible();

		expect(errors, `unexpected console errors:\n${errors.join('\n')}`).toEqual([]);
	});

	test('is hidden below the xl breakpoint', async ({ page }) => {
		await page.setViewportSize({ width: 1024, height: 800 });
		await login(page);
		// The rail still exists in the DOM but is display:none below xl.
		await expect(page.getByRole('complementary', { name: /Agent rail/i })).toBeHidden();
	});

	test('view + per-item approve/deny a filed access request via the dialog', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await login(page);

		const rail = page.getByRole('complementary', { name: /Agent rail/i });
		const filed = rail.getByText(/Access request filed: github read/i);
		await expect(filed).toBeVisible();

		// The filed row offers View + Deny (Approve lives inside the dialog).
		await expect(rail.getByRole('button', { name: 'View', exact: true })).toBeVisible();
		await rail.getByRole('button', { name: 'View', exact: true }).click();

		// The detail dialog opens with the request's items. Each pending item
		// renders as a card headed by its target (the toolkit/credential id or a
		// platform-scope string) with the requested action as a chip beside it.
		const dialog = page.getByRole('dialog', { name: 'Access request' });
		await expect(dialog).toBeVisible();
		await expect(dialog.getByRole('heading', { name: 'toolkit', level: 4 })).toBeVisible();
		await expect(dialog.getByRole('heading', { name: 'credential', level: 4 })).toBeVisible();

		// Step 1 (review) → "Review & submit" is gated until at least one item has
		// a verdict; deciding all of them enables it and advances to step 2.
		const review = dialog.getByRole('button', { name: /Review & submit/i });
		await expect(review).toBeDisabled();

		await dialog.getByRole('button', { name: 'Approve all' }).click();
		await expect(review).toBeEnabled();
		await review.click();

		// Step 2 (confirm) → commit the decision.
		await expect(dialog.getByText(/Step 2 of 2/i)).toBeVisible();
		await dialog.getByRole('button', { name: /Confirm decision/i }).click();

		// A terminal screen confirms the outcome; "Done" closes the dialog and the
		// row resolves (the View action slot disappears).
		await expect(dialog.getByRole('heading', { name: /Access granted/i })).toBeVisible();
		await dialog.getByRole('button', { name: 'Done' }).click();
		await expect(dialog).toBeHidden();
		await expect(rail.getByRole('button', { name: 'View', exact: true })).toBeHidden();
	});

	test('deny a whole filed access request from the row — reason-gated', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await login(page);

		const rail = page.getByRole('complementary', { name: /Agent rail/i });
		const filed = rail.getByText(/Access request filed: github read/i);
		await expect(filed).toBeVisible();

		await rail.getByRole('button', { name: 'Deny' }).click();

		// Deny reveals a reason field; Confirm stays disabled until it's filled.
		const reason = rail.getByLabel(/Reason \(sent back to the agent\)/i);
		await expect(reason).toBeVisible();
		const confirm = rail.getByRole('button', { name: /Confirm deny/i });
		await expect(confirm).toBeDisabled();

		await reason.fill('Scope too broad; narrow to a single repo.');
		await expect(confirm).toBeEnabled();
		await confirm.click();

		// After deciding, the row resolves (the decision action slot disappears).
		await expect(rail.getByRole('button', { name: /Confirm deny/i })).toBeHidden();
	});
});
