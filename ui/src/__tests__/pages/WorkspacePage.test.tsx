import { http, HttpResponse } from 'msw';
import { screen, renderWithProviders, userEvent, within, waitFor } from '../test-utils';
import { worker } from '../mocks/browser';
import WorkspacePage from '@/pages/WorkspacePage';

function renderWorkspace(route = '/workspace') {
	return renderWithProviders(<WorkspacePage />, { route, path: '/workspace' });
}

describe('WorkspacePage', () => {
	it('renders the page header, the stats strip, the filter input, and the catalog footer', async () => {
		renderWorkspace();

		expect(await screen.findByRole('heading', { name: /workspace/i })).toBeInTheDocument();
		expect(screen.getByTestId('workspace-stats-strip')).toBeInTheDocument();
		expect(screen.getByTestId('workspace-search')).toBeInTheDocument();
		expect(screen.getByTestId('workspace-catalog-footer')).toBeInTheDocument();
		// The catalog footer link routes to /discover.
		const catalogLink = screen.getByTestId('workspace-browse-catalog');
		expect(catalogLink).toHaveAttribute('href', '/discover');
	});

	it('does NOT mount the Discover toolbar (the catalog browser chrome)', async () => {
		renderWorkspace();
		await screen.findByRole('heading', { name: /workspace/i });
		// Workspace owns its own composition. If this assertion ever flips
		// it means we're back to reusing DiscoveryView and the surfaces are
		// going to look the same again.
		expect(screen.queryByTestId('discover-toolbar')).toBeNull();
		expect(screen.queryByTestId('discovery-filter-bar')).toBeNull();
	});

	it('issues a /apis request scoped to source=local (the workspace, not the catalog)', async () => {
		const seenSources: (string | null)[] = [];
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				seenSources.push(url.searchParams.get('source'));
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
		);
		renderWorkspace();
		await screen.findByRole('heading', { name: /workspace/i });
		await waitFor(() => {
			expect(seenSources.length).toBeGreaterThan(0);
		});
		// Every observed `/apis` call is workspace-scoped — there is no
		// merged or catalog-scoped fan-out from this page.
		expect(seenSources.every((s) => s === 'local')).toBe(true);
	});

	it('renders an APIs grid of WorkspaceTiles when the workspace has APIs', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'stripe.com',
							name: 'Stripe',
							description: 'Payments API',
							source: 'local',
							has_credentials: true,
						},
						{
							id: 'github.com',
							name: 'GitHub',
							description: 'Code hosting API',
							source: 'local',
							has_credentials: false,
						},
					],
					total: 2,
					page: 1,
				}),
			),
		);
		renderWorkspace();

		const apisSection = await screen.findByTestId('workspace-section-apis');
		const grid = await within(apisSection).findByTestId('workspace-grid-apis');
		const tiles = within(grid).getAllByTestId('workspace-tile-api');
		expect(tiles).toHaveLength(2);
		// Card meta reflects credential state — the workspace identity, not
		// a catalog "Available / Importable" pill.
		expect(within(tiles[0]).getByTestId('workspace-tile-creds-ok')).toBeInTheDocument();
		expect(within(tiles[1]).getByTestId('workspace-tile-creds-missing')).toBeInTheDocument();
	});

	it('renders the Workflows section with an empty CTA when there are no workflows yet', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/workflows', () => HttpResponse.json([])),
		);
		renderWorkspace();
		await screen.findByTestId('workspace-section-apis');
		// The section now stays mounted at zero workflows so we can offer
		// a primary "Add your first workflow" CTA — this replaced the
		// previous "hide entirely if zero" rule once the import dialog
		// gave us something useful to put inside the empty state.
		expect(await screen.findByTestId('workspace-section-workflows')).toBeInTheDocument();
		expect(screen.getByTestId('workspace-empty-workflow')).toBeInTheDocument();
		expect(screen.getByTestId('workspace-empty-cta-workflow')).toHaveTextContent(
			/add your first workflow/i,
		);
	});

	it('renders the Workflows section when workflows exist', async () => {
		worker.use(
			http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })),
			http.get('/workflows', () =>
				HttpResponse.json([
					{
						id: 'send-welcome',
						slug: 'send-welcome',
						name: 'Send welcome email',
						description: 'Welcome new signups via email',
						// Real `/workflows` shape — the listing returns
						// `steps_count` (number) and `involved_apis`
						// (string[]), not `steps[]` / `api_ids[]`. An
						// earlier version of this test used the wrong
						// names and silently disabled the meta-row check.
						steps_count: 3,
						involved_apis: ['sendgrid.com'],
					},
				]),
			),
		);
		renderWorkspace();

		const workflowsSection = await screen.findByTestId('workspace-section-workflows');
		const tile = await within(workflowsSection).findByTestId('workspace-tile-workflow');
		expect(within(tile).getByText(/send welcome email/i)).toBeInTheDocument();
		expect(within(tile).getByTestId('workspace-tile-steps')).toHaveTextContent(/3 steps/i);
		// Single involved API → one icon in the vendor pile.
		expect(within(tile).getByTestId('workspace-tile-vendor-pile')).toBeInTheDocument();
	});

	it('shows a vendor pile capped at 4 logos with a "+N" overflow chip on multi-API workflows', async () => {
		worker.use(
			http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })),
			http.get('/workflows', () =>
				HttpResponse.json([
					{
						id: 'big-fanout',
						slug: 'big-fanout',
						name: 'Cross-system reconcile',
						description: 'Touches a lot of upstreams',
						steps_count: 8,
						involved_apis: [
							'stripe.com',
							'zendesk.com',
							'hubspot.com',
							'slack.com',
							'asana.com',
							'github.com',
						],
					},
				]),
			),
		);
		renderWorkspace();

		const tile = await screen.findByTestId('workspace-tile-workflow');
		const pile = within(tile).getByTestId('workspace-tile-vendor-pile');
		// 6 vendors → 4 icons + "+2" chip.
		expect(within(pile).getByText(/^\+2$/)).toBeInTheDocument();
	});

	it('surfaces "Used by N toolkits" on API tiles whose credential is bound to a toolkit', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'stripe.com',
							name: 'Stripe',
							description: 'Payments API',
							source: 'local',
							has_credentials: true,
						},
						{
							id: 'github.com',
							name: 'GitHub',
							description: 'Code hosting API',
							source: 'local',
							has_credentials: false,
						},
					],
					total: 2,
					page: 1,
				}),
			),
			http.get('/toolkits', () =>
				HttpResponse.json([
					{
						id: 'tk-billing',
						name: 'Billing Ops',
						description: 'Billing reconciliation',
					},
					{ id: 'tk-support', name: 'Customer Support', description: 'CRM + Slack' },
				]),
			),
			http.get('/toolkits/tk-billing/credentials', () =>
				HttpResponse.json([
					{ credential_id: 'stripe-prod', api_id: 'stripe.com', label: 'Stripe prod' },
				]),
			),
			http.get('/toolkits/tk-support/credentials', () =>
				HttpResponse.json([
					{ credential_id: 'stripe-test', api_id: 'stripe.com', label: 'Stripe test' },
				]),
			),
		);
		renderWorkspace();

		const tiles = await screen.findAllByTestId('workspace-tile-api');
		const stripeTile = tiles.find((t) => t.dataset.tileId === 'stripe.com')!;
		const githubTile = tiles.find((t) => t.dataset.tileId === 'github.com')!;

		await waitFor(() => {
			expect(within(stripeTile).getByTestId('workspace-tile-toolkits')).toHaveTextContent(
				/used by 2 toolkits/i,
			);
		});
		// Tiles whose API isn't bound to any toolkit don't get the badge —
		// otherwise it'd be noise on every catalog import.
		expect(within(githubTile).queryByTestId('workspace-tile-toolkits')).toBeNull();
	});

	it('filters the visible tiles in-memory as the user types', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{ id: 'stripe.com', name: 'Stripe', source: 'local' },
						{ id: 'github.com', name: 'GitHub', source: 'local' },
					],
					total: 2,
					page: 1,
				}),
			),
		);
		renderWorkspace();

		await screen.findByTestId('workspace-section-apis');
		expect(screen.getAllByTestId('workspace-tile-api')).toHaveLength(2);

		await user.type(screen.getByLabelText(/filter workspace/i), 'strip');
		// In-memory filter — no /search fan-out, just narrows the tiles.
		await waitFor(() => {
			expect(screen.getAllByTestId('workspace-tile-api')).toHaveLength(1);
		});
		expect(screen.getByTestId('workspace-search-results-label')).toHaveTextContent(
			/1 of 2 match "strip"/i,
		);
	});

	it('exposes the page-help dialog via the "?" key', async () => {
		const user = userEvent.setup();
		renderWorkspace();
		await screen.findByRole('heading', { name: /workspace/i });

		(document.activeElement as HTMLElement | null)?.blur?.();
		await user.keyboard('?');
		expect(await screen.findByTestId('page-help-shortcuts')).toBeInTheDocument();
	});

	describe('Import flow', () => {
		it('opens the dialog directly when the header Add button is clicked, defaulting to the API kind', async () => {
			const user = userEvent.setup();
			renderWorkspace();
			await screen.findByRole('heading', { name: /workspace/i });

			await user.click(screen.getByTestId('workspace-add-button'));

			const dialog = await screen.findByTestId('import-source-dialog');
			// The kind selector is a radiogroup of <OptionCardSelector>
			// cards — the API card carries aria-checked="true" by default.
			const kindGroup = within(dialog).getByTestId('import-source-kind');
			const apiCard = within(kindGroup).getByRole('radio', { name: /api spec/i });
			expect(apiCard).toHaveAttribute('aria-checked', 'true');
			// And the primary CTA reflects the active kind.
			expect(within(dialog).getByTestId('import-source-submit')).toHaveTextContent(
				/import api/i,
			);
		});

		it("opens the dialog from each section's empty-state CTA with the right kind pre-selected", async () => {
			const user = userEvent.setup();
			worker.use(
				http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })),
				http.get('/workflows', () => HttpResponse.json([])),
			);
			renderWorkspace();

			await user.click(await screen.findByTestId('workspace-empty-cta-api'));
			let dialog = await screen.findByTestId('import-source-dialog');
			expect(
				within(within(dialog).getByTestId('import-source-kind')).getByRole('radio', {
					name: /api spec/i,
				}),
			).toHaveAttribute('aria-checked', 'true');
			// Close via the dialog's X (the footer no longer has a
			// Cancel button — Esc / X are the only cancel paths).
			await user.click(within(dialog).getByRole('button', { name: /close/i }));
			await user.click(screen.getByTestId('workspace-empty-cta-workflow'));
			dialog = await screen.findByTestId('import-source-dialog');
			expect(
				within(within(dialog).getByTestId('import-source-kind')).getByRole('radio', {
					name: /^workflow/i,
				}),
			).toHaveAttribute('aria-checked', 'true');
		});

		it('submits a URL import to POST /import, closes the dialog, and refreshes the workspace', async () => {
			const user = userEvent.setup();
			let postBody: { sources?: Array<Record<string, unknown>> } | null = null;
			let apiListCalls = 0;
			worker.use(
				http.get('/apis', () => {
					apiListCalls += 1;
					return HttpResponse.json({ data: [], total: 0, page: 1 });
				}),
				http.post('/import', async ({ request }) => {
					postBody = (await request.json()) as typeof postBody;
					return HttpResponse.json({
						results: [
							{
								index: 0,
								status: 'success',
								type: 'api',
								id: 'api.example.com',
							},
						],
					});
				}),
			);
			renderWorkspace();
			await screen.findByRole('heading', { name: /workspace/i });

			await waitFor(() => expect(apiListCalls).toBeGreaterThan(0));
			const initialApiCalls = apiListCalls;

			await user.click(screen.getByTestId('workspace-add-button'));

			const dialog = await screen.findByTestId('import-source-dialog');
			await user.type(
				within(dialog).getByTestId('import-source-url'),
				'https://example.com/openapi.json',
			);
			await user.click(within(dialog).getByTestId('import-source-submit'));

			await waitFor(() => {
				expect(screen.queryByTestId('import-source-dialog')).toBeNull();
			});
			expect(postBody).toEqual({
				sources: [{ type: 'url', url: 'https://example.com/openapi.json' }],
			});
			await waitFor(() => expect(apiListCalls).toBeGreaterThan(initialApiCalls));
		});

		it('renders the per-source error message inline and keeps the dialog open on import failure', async () => {
			const user = userEvent.setup();
			worker.use(
				http.post('/import', () =>
					HttpResponse.json({
						results: [
							{
								index: 0,
								status: 'error',
								error: 'Could not parse spec at https://example.com/openapi.json',
							},
						],
					}),
				),
			);
			renderWorkspace();
			await screen.findByRole('heading', { name: /workspace/i });

			await user.click(screen.getByTestId('workspace-add-button'));

			const dialog = await screen.findByTestId('import-source-dialog');
			await user.type(
				within(dialog).getByTestId('import-source-url'),
				'https://example.com/openapi.json',
			);
			await user.click(within(dialog).getByTestId('import-source-submit'));

			expect(await screen.findByTestId('import-source-error')).toHaveTextContent(
				/could not parse spec/i,
			);
			expect(screen.getByTestId('import-source-dialog')).toBeInTheDocument();
		});
	});
});
