import { test, expect, type Page } from '@playwright/test';

/**
 * Dashboard landing flow (mocked). Drives the real login → shell → `/app` index
 * and asserts the overview composed from the mocked list endpoints renders:
 * the pending-agents and alerts cards in particular (the brief's named flow).
 * Runs against MSW (Mode A) so it needs no backend.
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

test('dashboard landing shows pending-agents + alerts cards', async ({ page }) => {
	const errors = captureConsoleErrors(page);

	await page.goto('/app/');

	await page.getByLabel('Email').fill('admin@local');
	await page.getByRole('textbox', { name: 'Password' }).fill('password');
	await page.getByRole('button', { name: 'Sign in' }).click();

	await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

	// Pending-agents card renders. NOTE: `/agents` is registered by BOTH the
	// dashboard and agents modules in the shared MSW table; MSW v2 is
	// first-match-wins and `...agentsHandlers` is spread first, so in Mode A the
	// AGENTS fixture serves `/agents` here (not dashboard's `invoice-bot`). We
	// therefore assert the card + a row the winning handler provides
	// (`inbox-triage-bot`), rather than a dashboard-only fixture name. Scope to
	// the card's <h2> heading ("Awaiting approval" tile is a separate element).
	await expect(page.getByRole('heading', { name: 'Agents awaiting approval' })).toBeVisible();
	await expect(page.getByText('inbox-triage-bot')).toBeVisible();

	// Alerts card + a mocked actionable event. `/events` is owned ONLY by the
	// dashboard module, so its fixture (`Credential failing`) is stable here.
	// "Needs attention" appears twice (overview tile label + AlertsCard heading),
	// so scope to the card's <h2> heading to stay unambiguous.
	await expect(page.getByRole('heading', { name: 'Needs attention' })).toBeVisible();
	await expect(page.getByText('Credential failing')).toBeVisible();

	expect(errors, `unexpected console errors:\n${errors.join('\n')}`).toEqual([]);
});
