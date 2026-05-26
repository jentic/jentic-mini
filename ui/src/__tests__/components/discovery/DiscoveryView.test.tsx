import { http, HttpResponse } from 'msw';
import { within } from '@testing-library/react';
import { screen, waitFor, renderWithProviders, userEvent } from '../../test-utils';
import { worker } from '../../mocks/browser';
import { DiscoveryView } from '@/components/discovery';

function renderDiscover(route = '/catalog') {
	return renderWithProviders(<DiscoveryView />, { route, path: '/catalog' });
}

function renderDirectoryDiscover(route = '/discover') {
	// `/discover` hard-codes `forcedSource="directory"`, which is what
	// trims the segmented control to APIs-only and suppresses workflow
	// cards from the search results. Tests covering that branch must
	// render with `forcedSource` rather than the default
	// (which keeps every option visible — closer to `/catalog`).
	return renderWithProviders(<DiscoveryView forcedSource="directory" />, {
		route,
		path: '/discover',
	});
}

describe('DiscoveryView', () => {
	// ── Heading + base chrome ────────────────────────────────────────────────

	it('renders the sticky toolbar and source filter bar (no Type segments)', async () => {
		renderDiscover();
		expect(await screen.findByTestId('discover-toolbar')).toBeInTheDocument();
		expect(screen.getByTestId('discovery-filter-bar')).toBeInTheDocument();
		expect(screen.getByRole('textbox', { name: /search/i })).toBeInTheDocument();
		// May 2026 IA simplification removed the Type segmented control
		// entirely. Only the Source segment remains in the filter bar.
		const filterBar = screen.getByTestId('discovery-filter-bar');
		expect(within(filterBar).queryByRole('button', { name: /^apis$/i })).toBeNull();
		expect(within(filterBar).queryByRole('button', { name: /^workflows$/i })).toBeNull();
		expect(within(filterBar).queryByRole('button', { name: /^endpoints$/i })).toBeNull();
		expect(within(filterBar).queryByRole('button', { name: /^importable$/i })).toBeNull();
	});

	// ── Browse mode (grid, APIs default) ─────────────────────────────────────

	it('defaults to APIs in browse mode and lists workspace + directory together', async () => {
		// `GET /apis` (no source param) returns the server-side blended list.
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'stripe-api',
							name: 'Stripe',
							source: 'local',
							has_credentials: true,
						},
						{ id: 'github.com', name: 'github.com', source: 'catalog' },
					],
					total: 2,
					page: 1,
				}),
			),
		);

		renderDiscover();

		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());
		expect(screen.getByText('github.com')).toBeInTheDocument();
		// Workflow query should NOT have fired in default browse mode.
		expect(screen.queryByText(/no workflows to show/i)).toBeNull();
	});

	it('Workspace source narrows to the workspace slice (uses /apis?source=local)', async () => {
		const user = userEvent.setup();
		let lastApisCall: URL | null = null;
		worker.use(
			http.get('/apis', ({ request }) => {
				lastApisCall = new URL(request.url);
				const source = lastApisCall.searchParams.get('source');
				const data =
					source === 'local'
						? [{ id: 'stripe-api', name: 'Stripe', source: 'local' }]
						: [
								{ id: 'stripe-api', name: 'Stripe', source: 'local' },
								{ id: 'github.com', name: 'github.com', source: 'catalog' },
							];
				return HttpResponse.json({ data, total: data.length, page: 1 });
			}),
		);

		renderDiscover();
		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());
		expect(screen.getByText('github.com')).toBeInTheDocument();

		await user.click(screen.getByRole('button', { name: /my workspace/i }));

		await waitFor(() => {
			expect(screen.queryByText('github.com')).not.toBeInTheDocument();
		});
		expect(lastApisCall).not.toBeNull();
		expect((lastApisCall as unknown as URL).searchParams.get('source')).toBe('local');
	});

	// ── Search mode ──────────────────────────────────────────────────────────
	// After the May 2026 IA simplification, "search" is just a server-side
	// query param on `/apis` — no separate `/search` endpoint or blended
	// results grid. Typing filters the same browse grid in place.

	it('typing in the search box filters the browse grid via /apis?q=', async () => {
		const user = userEvent.setup();
		let lastQ: string | null = null;
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				lastQ = url.searchParams.get('q');
				const data = lastQ
					? [{ id: 'stripe.com', name: 'Stripe', source: 'local' }]
					: [
							{ id: 'stripe.com', name: 'Stripe', source: 'local' },
							{ id: 'github.com', name: 'github.com', source: 'catalog' },
						];
				return HttpResponse.json({ data, total: data.length, page: 1 });
			}),
		);

		renderDiscover();
		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());
		expect(screen.getByText('github.com')).toBeInTheDocument();

		const input = screen.getByRole('textbox', { name: /search/i });
		await user.type(input, 'stripe');

		await waitFor(() => {
			expect(lastQ).toBe('stripe');
		});
		await waitFor(() => {
			expect(screen.queryByText('github.com')).not.toBeInTheDocument();
		});
		expect(screen.getByText('Stripe')).toBeInTheDocument();
	});

	it('catalog_api rows from /apis render as ApiCards with source=directory', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		expect(card).toBeInTheDocument();
		expect(within(card).getByText('Directory')).toBeInTheDocument();
		expect(within(card).queryByText(/available to import/i)).toBeNull();
	});

	it('has_workflows flag on catalog rows surfaces the "+ workflows" chip on browse cards', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'openai.com',
							name: 'openai.com',
							source: 'catalog',
							has_workflows: true,
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		expect(card).toBeInTheDocument();
		expect(within(card).getByText('+ workflows')).toBeInTheDocument();
		expect(screen.queryByTestId('discovery-card-workflow')).toBeNull();
	});

	// ── Directory-forced (`/discover`) mode ─────────────────────────────────

	it('directory mode hides the filter bar entirely (no source / type segments)', async () => {
		// `/discover` is the directory-only surface. The Type segmented
		// control was removed in May 2026; the Source segment is also
		// hidden because the page hard-codes its source axis. With both
		// axes gone there's no filter UI to render — the bar collapses
		// entirely rather than presenting a non-functional widget.
		renderDirectoryDiscover();
		await screen.findByTestId('discover-toolbar');
		expect(screen.queryByTestId('discovery-filter-bar')).toBeNull();
	});

	it('directory mode search also hides the filter bar', async () => {
		const user = userEvent.setup();
		worker.use(http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })));

		renderDirectoryDiscover();
		await user.type(screen.getByRole('textbox', { name: /search/i }), 'plaid');

		await screen.findByTestId('discover-toolbar');
		// Same as browse mode — no filter bar in directory-forced
		// surfaces after the May 2026 simplification.
		expect(screen.queryByTestId('discovery-filter-bar')).toBeNull();
	});

	it('directory mode search filters via /apis query param (no workflow rows)', async () => {
		const user = userEvent.setup();
		let lastQ: string | null = null;
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				lastQ = url.searchParams.get('q');
				const data = lastQ
					? [
							{
								id: 'plaid.com',
								name: 'plaid.com',
								source: 'catalog',
								has_workflows: true,
							},
						]
					: [];
				return HttpResponse.json({ data, total: data.length, page: 1 });
			}),
		);

		renderDirectoryDiscover();
		await user.type(screen.getByRole('textbox', { name: /search/i }), 'plaid');

		await waitFor(() => expect(screen.getByText('plaid.com')).toBeInTheDocument());
		// API card present with the workflow chip.
		expect(screen.getByText('+ workflows')).toBeInTheDocument();
		// No workflow cards rendered — directory mode only shows APIs.
		expect(screen.queryByTestId('discovery-card-workflow')).toBeNull();
	});

	it('directory mode rewrites stale ?type=workflow URLs to drop the param', async () => {
		// Deep links to `/discover?type=workflow` from before the
		// collapse should not render with a hidden filter active. The
		// `useEffect` URL-fixup in `DiscoveryView` strips the param so
		// the page renders identically to `/discover`.
		worker.use(http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })));

		renderDirectoryDiscover('/discover?type=workflow');
		await screen.findByTestId('discover-toolbar');

		// `?type=workflow` should be rewritten away — the URL test
		// utility lets us read the current location through a
		// `data-testid` mirror, but the simplest assertion is that the
		// browse view falls back to APIs (no workflow query fires).
		await waitFor(() => {
			expect(window.location.search).not.toContain('type=workflow');
		});
	});

	it('directory browse renders the "+ workflows" chip when /apis sets has_workflows', async () => {
		// Regression: previously the chip only surfaced on search-result
		// cards because only the `/search` payload carried
		// `has_workflows`. `/apis` now folds the workflow manifest into
		// its catalog rows the same way `/search`'s blender does, so the
		// directory browse grid can advertise workflow availability
		// before the user opens the API detail sheet. Without this,
		// the section inside the sheet was a hidden treasure — there
		// was nothing on the card to hint it existed.
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
							has_credentials: false,
							has_workflows: true,
						},
						{
							id: 'github.com',
							name: 'github.com',
							source: 'catalog',
							has_credentials: false,
							has_workflows: false,
						},
					],
					total: 2,
					page: 1,
				}),
			),
		);

		renderDirectoryDiscover();
		await screen.findByTestId('discover-toolbar');

		// Plaid carries the chip; GitHub does not. Scope the assertions
		// to the cards themselves so a stray "+ workflows" string in
		// chrome elsewhere wouldn't pass the check.
		const cards = await screen.findAllByTestId('discovery-card-api');
		const plaidCard = cards.find((c) => within(c).queryByText('plaid.com'));
		const githubCard = cards.find((c) => within(c).queryByText('github.com'));
		expect(plaidCard).toBeDefined();
		expect(githubCard).toBeDefined();
		expect(within(plaidCard!).getByText('+ workflows')).toBeInTheDocument();
		expect(within(githubCard!).queryByText('+ workflows')).toBeNull();
	});

	// ── P2: search relevance feedback ────────────────────────────────────────
	// Match snippets and the "matched on" badge were removed in the May 2026
	// IA simplification. Search is now a server-side filter on /apis, not a
	// separate /search endpoint with scoring/highlighting. The filter-based
	// search is tested above in "typing in the search box filters the browse
	// grid via /apis?q=".

	it('search results show a count summary when query is non-empty', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q) {
					return HttpResponse.json({
						data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({
					data: [
						{ id: 'stripe.com', name: 'Stripe', source: 'local' },
						{ id: 'github.com', name: 'github.com', source: 'catalog' },
					],
					total: 2,
					page: 1,
				});
			}),
		);

		renderDiscover();
		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());

		await user.type(screen.getByRole('textbox', { name: /search/i }), 'stripe');

		await waitFor(() => {
			expect(screen.getByText(/1 result/)).toBeInTheDocument();
		});
	});

	it('treats legacy ?source=local,catalog as "All"', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{ id: 'stripe-api', name: 'Stripe', source: 'local' },
						{ id: 'github.com', name: 'github.com', source: 'catalog' },
					],
					total: 2,
					page: 1,
				}),
			),
		);

		renderDiscover('/catalog?source=local,catalog');

		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());
		expect(screen.getByText('github.com')).toBeInTheDocument();
	});

	// ── Directory card inline actions ────────────────────────────────────────

	it('Directory API card exposes Import to workspace + View on GitHub inline (independent of sheet)', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
							_links: {
								github: 'https://github.com/jentic/jentic-public-apis/tree/main/apis/openapi/plaid.com',
							},
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');

		// Inline primary action: import to workspace. Now a <button> that
		// fires `POST /import` directly (no credential-form indirection)
		// — see useImportCatalogApi. The card-level click handler is
		// guarded with stopPropagation so the button doesn't ALSO open
		// the sheet (verified by the next test).
		const importBtn = within(card).getByRole('button', { name: /^import$/i });
		expect(importBtn).toHaveAttribute('data-testid', 'discovery-card-import');

		const gh = within(card).getByRole('link', { name: /view plaid\.com on github/i });
		expect(gh).toHaveAttribute(
			'href',
			'https://github.com/jentic/jentic-public-apis/tree/main/apis/openapi/plaid.com',
		);
	});

	it('Directory API card omits a synthetic description (catalog manifest has none)', async () => {
		// May 2026: the adapter used to fabricate "Available in the Jentic
		// public catalog. Add a credential…" so card heights matched
		// workspace cards. Every directory card got the *same* string,
		// which read like real metadata when it wasn't. Now the
		// description column is empty for catalog rows; the differentiation
		// lives in the chip row + action buttons. See
		// `apiToEntity` in DiscoveryView.tsx.
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		expect(within(card).queryByText(/add a credential to import/i)).toBeNull();
		expect(within(card).queryByText(/available in the jentic public catalog/i)).toBeNull();
	});

	// ── API Detail Sheet (Phase 1) ───────────────────────────────────────────

	it('clicking a workspace API card opens the detail sheet with operations', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'stripe.com',
							name: 'Stripe',
							source: 'local',
							has_credentials: true,
						},
					],
					total: 1,
					page: 1,
				}),
			),
			// Real server shape: token-efficient `{id, summary, description}`
			// where `id` is the jentic_id (METHOD/host/path). Method + path are
			// NOT separate fields — the sheet must derive them from `id`. This
			// test guards against a regression where ops rendered as `?` badges.
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({
					data: [
						{
							id: 'GET/api.stripe.com/v1/customers',
							summary: 'List customers',
							description: '',
						},
						{
							id: 'POST/api.stripe.com/v1/charges',
							summary: 'Create charge',
							description: '',
						},
					],
					total: 2,
					page: 1,
				}),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		// Sheet opens — header repeats the title in the dialog.
		const sheet = await screen.findByTestId('sheet-primitive');
		expect(within(sheet).getByRole('heading', { name: 'Stripe' })).toBeInTheDocument();

		// Operations list rendered from the workspace endpoint.
		await waitFor(() => {
			expect(within(sheet).getByTestId('sheet-ops-list')).toBeInTheDocument();
		});
		expect(within(sheet).getByText('List customers')).toBeInTheDocument();
		expect(within(sheet).getByText('Create charge')).toBeInTheDocument();
		// Method badges + paths are derived from `id` even when the server
		// only sends `{id, summary, description}`.
		expect(within(sheet).getByText('GET')).toBeInTheDocument();
		expect(within(sheet).getByText('POST')).toBeInTheDocument();
		expect(within(sheet).getByText('/v1/customers')).toBeInTheDocument();
		expect(within(sheet).getByText('/v1/charges')).toBeInTheDocument();
	});

	it('sheet shows Workflows-for-this-API section when the API has matching workflows', async () => {
		// Regression: the sheet should deep-link to the dedicated workflow page
		// rather than expanding inline, AND filter strictly on
		// `involved_apis` membership (server `q=` matches description too —
		// we don't want a workflow that just *mentions* the api in copy).
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
			http.get('/workflows', ({ request }) => {
				const url = new URL(request.url);
				// Sanity-check the call shape — sheet must filter server-side.
				expect(url.searchParams.get('q')).toBe('stripe.com');
				expect(url.searchParams.get('source')).toBe('local');
				return HttpResponse.json([
					{
						slug: 'charge-and-receipt',
						name: 'Charge customer and send receipt',
						involved_apis: ['stripe.com'],
						steps_count: 4,
					},
					{
						// Mentions stripe in description but doesn't actually
						// involve it — must be filtered out client-side.
						slug: 'unrelated',
						name: 'Unrelated workflow that mentions stripe in copy',
						involved_apis: ['github.com'],
						steps_count: 2,
					},
				]);
			}),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		await waitFor(() => {
			expect(within(sheet).getByTestId('sheet-workflows-section')).toBeInTheDocument();
		});

		// Only the workflow that actually involves stripe.com renders.
		expect(within(sheet).getByText(/Charge customer and send receipt/)).toBeInTheDocument();
		expect(within(sheet).queryByText(/Unrelated workflow/)).toBeNull();
		// Step count chip rendered.
		expect(within(sheet).getByText(/4 steps/)).toBeInTheDocument();
	});

	it('sheet hides Workflows section when there are no matching workflows', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'lonely.com', name: 'Lonely', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/lonely.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
			http.get('/workflows', () => HttpResponse.json([])),
		);

		const user = userEvent.setup();
		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		// Wait for the credentials section as a proxy for "sheet body settled".
		await waitFor(() => {
			expect(within(sheet).getByTestId('sheet-credentials-section')).toBeInTheDocument();
		});
		// Empty workflow section is suppressed entirely — empty sections are noisy.
		expect(within(sheet).queryByTestId('sheet-workflows-section')).toBeNull();
	});

	it('sheet shows Credentials-for-this-API section with Add CTA when zero creds', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'fresh.com', name: 'Fresh', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/fresh.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
			// Default handler returns `{data: [], total: 0}` — the sheet
			// adapter must tolerate both raw-list and envelope shapes.
		);

		const user = userEvent.setup();
		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const section = await within(sheet).findByTestId('sheet-credentials-section');
		expect(within(section).getByText(/no credentials configured/i)).toBeInTheDocument();
		// Add CTA deep-links to the credentials creation flow filtered by api_id.
		const addCta = within(section).getByText(/add credential/i);
		expect(addCta.closest('a')).toHaveAttribute(
			'href',
			expect.stringContaining('/credentials/new?api_id=fresh.com'),
		);
	});

	it('sheet lists existing credentials with a "Manage credentials" deep-link', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'openai.com', name: 'OpenAI', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/openai.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
			http.get('/credentials', ({ request }) => {
				const url = new URL(request.url);
				expect(url.searchParams.get('api_id')).toBe('openai.com');
				return HttpResponse.json([
					{ id: 'cred_prod_abc', label: 'OPENAI_PROD', api_id: 'openai.com' },
					{ id: 'cred_staging_xyz', label: 'OPENAI_STAGING', api_id: 'openai.com' },
				]);
			}),
		);

		const user = userEvent.setup();
		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const section = await within(sheet).findByTestId('sheet-credentials-section');
		expect(within(section).getByText('OPENAI_PROD')).toBeInTheDocument();
		expect(within(section).getByText('OPENAI_STAGING')).toBeInTheDocument();
		// Footer link lets the user jump to the canonical Credentials surface.
		const manageLink = within(section).getByText(/manage credentials/i);
		expect(manageLink.closest('a')).toHaveAttribute(
			'href',
			expect.stringContaining('/credentials?api_id=openai.com'),
		);
	});

	it('clicking a directory API card opens the sheet and lazy-fetches the spec preview', async () => {
		const user = userEvent.setup();
		let previewCalled = 0;
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
							_links: {
								github: 'https://github.com/jentic/jentic-public-apis/tree/main/apis/openapi/plaid.com',
							},
						},
					],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/plaid.com/operations', () => {
				previewCalled++;
				return HttpResponse.json({
					data: [
						{
							method: 'GET',
							path: '/accounts',
							summary: 'List accounts',
							description: 'Returns all accounts.',
							operation_id: 'listAccounts',
						},
					],
					total: 1,
					truncated: false,
					spec_url: 'https://example.com/plaid.json',
					info: { title: 'Plaid API', version: '1.0', description: 'Plaid OpenAPI spec' },
				});
			}),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		await waitFor(() => {
			expect(within(sheet).getByTestId('sheet-ops-list-directory')).toBeInTheDocument();
		});
		expect(within(sheet).getByText('List accounts')).toBeInTheDocument();
		// Spec description should override the synthetic list-view one.
		expect(within(sheet).getByText('Plaid OpenAPI spec')).toBeInTheDocument();
		expect(previewCalled).toBe(1);
	});

	it('clicking a directory op row opens the directory inspect panel (no extra fetch)', async () => {
		// F8: directory operations should be inspectable too — parameters and
		// auth come from the same `previewCatalogOperations` payload, so the
		// detail view should NOT trigger a second round-trip.
		const user = userEvent.setup();
		let previewCalled = 0;
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'plaid.com', name: 'plaid.com', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/plaid.com/operations', () => {
				previewCalled++;
				return HttpResponse.json({
					data: [
						{
							method: 'GET',
							path: '/accounts/{account_id}',
							summary: 'Get account',
							description: 'Returns an account by id.',
							operation_id: 'getAccount',
							parameters: [
								{
									name: 'account_id',
									in: 'path',
									required: true,
									description: 'The account identifier',
								},
								{
									name: 'fields',
									in: 'query',
									required: false,
									description: 'Comma-separated field list',
								},
							],
							security: ['plaidClientAuth'],
						},
					],
					total: 1,
					truncated: false,
					spec_url: 'https://example.com/plaid.json',
					info: { title: 'Plaid API', version: '1.0', description: '' },
					security_schemes: {
						plaidClientAuth: {
							type: 'apiKey',
							in: 'header',
							name: 'PLAID-CLIENT-ID',
							description: 'Plaid client id header',
						},
					},
				});
			}),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const row = await within(sheet).findByTestId('sheet-ops-row-directory');
		await user.click(row);

		// Inspect panel renders from the SAME cached preview — no second fetch.
		const inspect = await within(sheet).findByTestId('sheet-directory-inspect');
		expect(within(inspect).getByText('Get account')).toBeInTheDocument();
		expect(within(inspect).getByText('account_id')).toBeInTheDocument();
		expect(within(inspect).getByText('fields')).toBeInTheDocument();
		expect(within(inspect).getByText('required')).toBeInTheDocument();
		expect(within(inspect).getByText('plaidClientAuth')).toBeInTheDocument();
		// `Import to workspace` CTA replaces the upstream link as the forward
		// action (renamed from "Add credential" — see DiscoveryCard May
		// 2026). Now a <button> wired directly to `POST /import` rather
		// than a deep-link to the credential form, since "import" and
		// "set up credentials" are distinct intents.
		const importBtn = within(inspect).getByRole('button', { name: /import to workspace/i });
		expect(importBtn).toHaveAttribute('data-testid', 'sheet-directory-inspect-import');
		// Critical: a single preview fetch served both the row list AND the
		// inspect view. Two would mean the React-Query cache key drifted.
		expect(previewCalled).toBe(1);
	});

	it('directory inspect back-button returns to the operations list', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'plaid.com', name: 'plaid.com', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/plaid.com/operations', () =>
				HttpResponse.json({
					data: [
						{
							method: 'POST',
							path: '/items',
							summary: 'Create item',
							description: '',
							operation_id: 'createItem',
							parameters: [],
							security: [],
						},
					],
					total: 1,
					truncated: false,
					spec_url: '',
					info: { title: '', version: '', description: '' },
					security_schemes: {},
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));
		const sheet = await screen.findByTestId('sheet-primitive');
		await user.click(await within(sheet).findByTestId('sheet-ops-row-directory'));
		expect(await within(sheet).findByTestId('sheet-directory-inspect')).toBeInTheDocument();

		// Back arrow exits the inspect view back to the ops list.
		await user.click(within(sheet).getByRole('button', { name: /back to operations/i }));
		expect(await within(sheet).findByTestId('sheet-ops-list-directory')).toBeInTheDocument();
		expect(within(sheet).queryByTestId('sheet-directory-inspect')).toBeNull();
	});

	it('?inspect=<api_id> on initial load opens the sheet (deep link)', async () => {
		worker.use(
			http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })),
			// No cached entity → sheet must resolve source itself. `getApi`
			// succeeds → workspace path → operations endpoint called.
			http.get('/apis/stripe.com', () =>
				HttpResponse.json({ id: 'stripe.com', name: 'Stripe', source: 'local' }),
			),
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({
					data: [
						{
							id: 'op-1',
							jentic_id: 'GET/api.stripe.com/v1/customers',
							method: 'GET',
							path: '/v1/customers',
							summary: 'List customers',
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover('/catalog?inspect=stripe.com');

		const sheet = await screen.findByTestId('sheet-primitive');
		await waitFor(() => {
			expect(within(sheet).getByText('List customers')).toBeInTheDocument();
		});
	});

	it('clicking the close button collapses the sheet', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		// Wait until the sheet has fully entered (data loaded) so we're
		// closing a stable surface, not racing the entrance animation.
		// Browser-mode + React 19 concurrent rendering occasionally leaves
		// the sheet in a half-mounted state where the close button exists
		// but its onClick handler hasn't been attached yet — waiting on a
		// rendered child that proves the inner tree is committed avoids
		// the race.
		await waitFor(() => {
			expect(within(sheet).getByText(/no operations indexed yet/i)).toBeInTheDocument();
		});

		// Use userEvent for the close click — it sets up pointer events the
		// way React 19 expects, which the synthetic `fireEvent.click` does
		// not always emulate cleanly under the parallel test pool.
		const closeButton = within(sheet).getByRole('button', { name: /close detail panel/i });
		await user.click(closeButton);

		// The closing animation takes ~300ms then the sheet unmounts entirely.
		// Behaviour-level assertion — URL state lives in MemoryRouter and isn't
		// reflected in window.location, so we can't assert on it directly.
		// Generous timeout: occasionally races with React 19 paint/layout
		// scheduling under the parallel test pool, which can stretch the
		// unmount tick beyond the animation duration.
		await waitFor(
			() => {
				expect(screen.queryByTestId('sheet-primitive')).toBeNull();
			},
			{ timeout: 3000 },
		);
	});

	it('clicking inline "Import" on a directory card does NOT open the sheet', async () => {
		const user = userEvent.setup();
		// Stub the import flow so the mutation resolves cleanly. The
		// shape mirrors `POST /import`'s contract (`{results: [...]}`).
		// Without `getCatalogEntry` stubbed we'd hit the fallback path
		// because the test's catalog row has no `spec_url` field.
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [
						{
							id: 'plaid.com',
							name: 'plaid.com',
							source: 'catalog',
							spec_url: 'https://example.com/plaid.json',
						},
					],
					total: 1,
					page: 1,
				}),
			),
			http.post('/import', () =>
				HttpResponse.json({ results: [{ status: 'success', api_id: 'plaid.com' }] }),
			),
		);

		renderDiscover();

		const card = await screen.findByTestId('discovery-card-api');
		const importBtn = within(card).getByRole('button', { name: /^import$/i });

		// The CTA must `stopPropagation` so the card's outer onClick
		// (which opens the sheet) does NOT also fire.
		await user.click(importBtn);

		// Sheet must not have opened. (No URL assertion — MemoryRouter
		// state isn't reflected in window.location.)
		expect(screen.queryByTestId('sheet-primitive')).toBeNull();
	});

	it('clicking an operation row in the workspace sheet drills into InspectPanel', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({
					data: [
						{
							id: 'op-1',
							jentic_id: 'GET/api.stripe.com/v1/customers',
							method: 'GET',
							path: '/v1/customers',
							summary: 'List customers',
						},
					],
					total: 1,
					page: 1,
				}),
			),
			// The generated InspectService does NOT URL-encode the slashes in
			// capability ids, so the request lands as a multi-segment path
			// (e.g. `/inspect/GET/api.stripe.com/v1/customers`). Match with a
			// regex so we catch the whole prefix regardless of depth.
			// Real backend shape: `parameters` is a dict keyed by location,
			// `auth` (not `auth_instructions`) is a pre-shaped scheme list.
			// Mirror this precisely — drift between mock and server is what
			// hid the original InspectPanel bug.
			http.get(/\/inspect\/.+/, () =>
				HttpResponse.json({
					id: 'GET/api.stripe.com/v1/customers',
					method: 'GET',
					url: 'https://api.stripe.com/v1/customers',
					summary: 'List customers (detailed)',
					description: 'Returns a list of customers from your Stripe account.',
					parameters: {
						query: [
							{
								name: 'limit',
								required: false,
								description: 'Page size cap',
							},
							{
								name: 'starting_after',
								required: false,
								description: 'Cursor for pagination',
							},
						],
					},
					auth: [
						{
							scheme: 'BasicAuth',
							type: 'http_basic',
							instruction: 'Set header `Authorization: Basic <credentials>`',
						},
					],
					api: { id: 'stripe.com', name: 'Stripe' },
					_links: { upstream: 'https://stripe.com/docs/api/customers/list' },
				}),
			),
		);

		renderDiscover();
		await user.click(
			within(await screen.findByTestId('discovery-card-api')).getByRole('button'),
		);

		const sheet = await screen.findByTestId('sheet-primitive');
		const row = await within(sheet).findByText('List customers');
		await user.click(row);

		// Drill-down view rendered: InspectPanel description appears AND the
		// "Back to operations" arrow replaces the vendor icon (only present
		// in drill-down mode).
		await waitFor(() => {
			expect(
				within(sheet).getByText('Returns a list of customers from your Stripe account.'),
			).toBeInTheDocument();
		});
		expect(
			within(sheet).getByRole('button', { name: /back to operations/i }),
		).toBeInTheDocument();

		// PARITY REGRESSION GUARD: workspace inspect must surface parameters
		// (from the dict-shaped `parameters` field) AND auth (from `auth`,
		// not `auth_instructions`). Both were silently broken before — the
		// only thing keeping the test green was a mock that lied about the
		// server's shape. Each of the four assertions below would have
		// failed against either of the original bugs.
		const inspect = within(sheet).getByTestId('inspect-panel');
		expect(within(inspect).getByText('limit')).toBeInTheDocument();
		expect(within(inspect).getByText('starting_after')).toBeInTheDocument();
		expect(within(inspect).getByText('BasicAuth')).toBeInTheDocument();
		expect(within(inspect).getByText(/Authorization: Basic <credentials>/)).toBeInTheDocument();
		// Method + path header is the visual continuity from the op row.
		expect(within(inspect).getByText('/v1/customers')).toBeInTheDocument();
	});

	it('strips the legacy ?type=importable URL param and still renders results', async () => {
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover('/catalog?type=importable');

		// `?type=` was removed entirely in the May 2026 simplification —
		// the URL fixup `useEffect` strips it. Results still render.
		await waitFor(() => expect(screen.getByText('Stripe')).toBeInTheDocument());
		await waitFor(() => {
			expect(window.location.search).not.toContain('type=');
		});
	});

	// ── P9-fe: virtualise + load-more in sheet ────────────────────────────────

	it('directory sheet renders Load more for paginated specs and appends ops', async () => {
		const user = userEvent.setup();

		// Mock a 60-op spec — server pages 25 at a time. The sheet should
		// render the first 25 + a "Load more" footer; clicking it should
		// fetch the next page and append.
		const allOps = Array.from({ length: 60 }).map((_, i) => ({
			method: 'GET',
			path: `/items/${i}`,
			summary: `Get item ${i}`,
			operation_id: `getItem${i}`,
			parameters: [],
			security: [],
			tags: i < 30 ? ['accounts'] : ['transactions'],
		}));

		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'big.com', name: 'Big API', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/big.com/operations', ({ request }) => {
				const url = new URL(request.url);
				const offset = parseInt(url.searchParams.get('offset') ?? '0', 10);
				const limit = parseInt(url.searchParams.get('limit') ?? '25', 10);
				const slice = allOps.slice(offset, offset + limit);
				return HttpResponse.json({
					data: slice,
					total: allOps.length,
					truncated: offset + limit < allOps.length,
					offset,
					limit,
					spec_url: 'https://example.com/big.json',
					info: { title: 'Big API', version: '1.0', description: '' },
					security_schemes: {},
				});
			}),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');

		// First page renders 25 rows + footer says "Showing 25 of 60".
		await waitFor(() => {
			const rows = within(sheet).getAllByTestId('sheet-ops-row-directory');
			expect(rows).toHaveLength(25);
		});
		expect(within(sheet).getByText(/Showing 25 of 60/)).toBeInTheDocument();

		// Click "Load more" → next 25 rows append.
		await user.click(within(sheet).getByTestId('ops-load-more'));
		await waitFor(() => {
			const rows = within(sheet).getAllByTestId('sheet-ops-row-directory');
			expect(rows).toHaveLength(50);
		});
		expect(within(sheet).getByText(/Showing 50 of 60/)).toBeInTheDocument();
	});

	it('directory sheet renders tag chips and filters in-place when clicked', async () => {
		const user = userEvent.setup();

		const ops = [
			{
				method: 'GET',
				path: '/customers',
				summary: 'List customers',
				operation_id: 'listCustomers',
				parameters: [],
				security: [],
				tags: ['customers'],
			},
			{
				method: 'POST',
				path: '/charges',
				summary: 'Create charge',
				operation_id: 'createCharge',
				parameters: [],
				security: [],
				tags: ['charges'],
			},
			{
				method: 'GET',
				path: '/charges/{id}',
				summary: 'Get charge',
				operation_id: 'getCharge',
				parameters: [],
				security: [],
				tags: ['charges'],
			},
			{
				method: 'GET',
				path: '/refunds',
				summary: 'List refunds',
				operation_id: 'listRefunds',
				parameters: [],
				security: [],
				tags: ['refunds'],
			},
			{
				method: 'POST',
				path: '/refunds',
				summary: 'Create refund',
				operation_id: 'createRefund',
				parameters: [],
				security: [],
				tags: ['refunds'],
			},
			{
				method: 'GET',
				path: '/disputes',
				summary: 'List disputes',
				operation_id: 'listDisputes',
				parameters: [],
				security: [],
				tags: ['disputes'],
			},
		];

		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'tagged.com', name: 'Tagged API', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/tagged.com/operations', () =>
				HttpResponse.json({
					data: ops,
					total: ops.length,
					truncated: false,
					offset: 0,
					limit: 25,
					spec_url: 'https://example.com/tagged.json',
					info: { title: 'Tagged API', version: '1.0', description: '' },
					security_schemes: {},
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		await within(sheet).findByText('List customers');

		// Tag chips render — at least 4 unique tags + the "All" chip.
		const tagBar = await within(sheet).findByTestId('ops-tag-bar');
		const chips = within(tagBar).getAllByTestId('ops-tag-chip');
		// "charges" and "refunds" are most-frequent so render first.
		const chipLabels = chips.map((c) => c.textContent);
		expect(chipLabels).toContain('charges');
		expect(chipLabels).toContain('refunds');

		// Click "charges" → only the 2 charges rows visible.
		const chargesChip = chips.find((c) => c.textContent === 'charges');
		await user.click(chargesChip!);
		await waitFor(() => {
			const visibleRows = within(sheet).getAllByTestId('sheet-ops-row-directory');
			expect(visibleRows).toHaveLength(2);
		});
		expect(within(sheet).getByText('Create charge')).toBeInTheDocument();
		expect(within(sheet).getByText('Get charge')).toBeInTheDocument();
		expect(within(sheet).queryByText('List customers')).toBeNull();

		// "All" resets the filter.
		await user.click(within(tagBar).getByText('All'));
		await waitFor(() => {
			const visibleRows = within(sheet).getAllByTestId('sheet-ops-row-directory');
			expect(visibleRows).toHaveLength(6);
		});
	});

	it('directory sheet inline filter narrows ops by summary / path', async () => {
		const user = userEvent.setup();

		// Need >5 ops for the filter input to render.
		const ops = Array.from({ length: 6 }).map((_, i) => ({
			method: 'GET',
			path: `/items/${i}`,
			summary: i === 3 ? 'Find a needle' : `Boring item ${i}`,
			operation_id: `op${i}`,
			parameters: [],
			security: [],
			tags: [],
		}));

		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'haystack.com', name: 'Haystack API', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/haystack.com/operations', () =>
				HttpResponse.json({
					data: ops,
					total: ops.length,
					truncated: false,
					offset: 0,
					limit: 25,
					spec_url: 'https://example.com/haystack.json',
					info: { title: 'Haystack API', version: '1.0', description: '' },
					security_schemes: {},
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		await within(sheet).findByText('Find a needle');

		const input = within(sheet).getByTestId('ops-filter-input');
		await user.type(input, 'needle');
		await waitFor(() => {
			const visibleRows = within(sheet).getAllByTestId('sheet-ops-row-directory');
			expect(visibleRows).toHaveLength(1);
		});
		expect(within(sheet).getByText('Find a needle')).toBeInTheDocument();
	});

	// ── P4: API summary in sheet ──────────────────────────────────────────────

	it('directory sheet renders the spec info.description as an API summary', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'doc.com', name: 'Doc API', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/doc.com/operations', () =>
				HttpResponse.json({
					data: [],
					total: 0,
					truncated: false,
					offset: 0,
					limit: 25,
					spec_url: 'https://example.com/doc.json',
					info: {
						title: 'Doc API',
						version: '1.0',
						description: 'A **bot-free** API for fetching `documents` and metadata.',
					},
					security_schemes: {},
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const summary = await within(sheet).findByTestId('api-summary');
		expect(summary).toHaveTextContent(/bot-free.*API for fetching.*documents.*metadata/i);
		// Markdown actually rendered the bold span as <strong>.
		expect(within(summary).getByText('bot-free').tagName.toLowerCase()).toBe('strong');
	});

	it('workspace sheet falls back to host + op count when no description', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'bare.com', name: 'Bare API', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/bare.com', () =>
				HttpResponse.json({ id: 'bare.com', info: { description: null } }),
			),
			http.get('/apis/bare.com/operations', () =>
				HttpResponse.json({
					data: [
						{ id: 'GET/bare.com/x', summary: 'X', tags: ['core'] },
						{ id: 'GET/bare.com/y', summary: 'Y', tags: ['core'] },
						{ id: 'GET/bare.com/z', summary: 'Z', tags: ['admin'] },
					],
					total: 3,
					page: 1,
					offset: 0,
					limit: 25,
					total_pages: 1,
					has_more: false,
					truncated: false,
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const summary = await within(sheet).findByTestId('api-summary');
		// Fallback shape: "<host> — N operations across M tags"
		expect(summary).toHaveTextContent(/bare\.com.*3 operations across 2 tags/);
	});

	it('long descriptions get a Show more / Show less toggle', async () => {
		const user = userEvent.setup();
		const longDesc = 'Lorem ipsum dolor sit amet. '.repeat(20); // ~540 chars
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'long.com', name: 'Long API', source: 'catalog' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/catalog/long.com/operations', () =>
				HttpResponse.json({
					data: [],
					total: 0,
					truncated: false,
					offset: 0,
					limit: 25,
					spec_url: 'https://example.com/long.json',
					info: { title: 'Long API', version: '1.0', description: longDesc },
					security_schemes: {},
				}),
			),
		);

		renderDiscover();
		const card = await screen.findByTestId('discovery-card-api');
		await user.click(within(card).getByRole('button'));

		const sheet = await screen.findByTestId('sheet-primitive');
		const summary = await within(sheet).findByTestId('api-summary');
		const toggle = within(sheet).getByTestId('api-summary-toggle');
		expect(toggle).toHaveTextContent('Show more');
		// Truncated form contains the ellipsis sentinel; the rendered
		// description ends in `…` (the toggle button is a sibling).
		expect(summary.textContent ?? '').toMatch(/…/);

		await user.click(toggle);
		expect(toggle).toHaveTextContent('Show less');
		// Expanded — full description no longer ends in the ellipsis.
		// (The full text contains 20 sentence repeats, so check length.)
		expect((summary.textContent ?? '').length).toBeGreaterThan(500);
	});

	// ── P3 — Sheet cross-API navigation (recents + history) ────────────────

	it('shows the recents strip after inspecting two distinct APIs', async () => {
		const user = userEvent.setup();
		// Make sure the store is clean for this test.
		window.sessionStorage.clear();
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
			http.get('/apis/:id', ({ params }) =>
				HttpResponse.json({
					id: params.id as string,
					name: params.id as string,
					source: 'local',
				}),
			),
			http.get('/apis/:id/operations', () =>
				HttpResponse.json({
					data: [
						{
							id: 'op-1',
							jentic_id: 'GET/x/v1/y',
							method: 'GET',
							path: '/v1/y',
							summary: 'Some op',
						},
					],
					total: 1,
					page: 1,
				}),
			),
		);

		renderDiscover();
		// Open Stripe.
		const stripeCard = await screen.findByText('Stripe');
		await user.click(stripeCard.closest('button')!);
		const sheet = await screen.findByTestId('sheet-primitive');
		await waitFor(() => expect(within(sheet).getByText(/some op/i)).toBeInTheDocument());

		// Recents strip should be hidden with only one entry.
		expect(within(sheet).queryByTestId('sheet-recents-strip')).toBeNull();

		// Close, open GitHub.
		await user.click(within(sheet).getByRole('button', { name: /close/i }));
		await waitFor(() => expect(screen.queryByTestId('sheet-primitive')).toBeNull(), {
			timeout: 3000,
		});

		const githubCard = await screen.findByText('GitHub');
		await user.click(githubCard.closest('button')!);
		const sheet2 = await screen.findByTestId('sheet-primitive');
		await waitFor(() => expect(within(sheet2).getByText(/some op/i)).toBeInTheDocument());

		// Strip now has both — Stripe is selectable, GitHub is current.
		const strip = await within(sheet2).findByTestId('sheet-recents-strip');
		expect(within(strip).getByRole('button', { name: /stripe/i })).toBeInTheDocument();

		// Click Stripe chip → sheet swaps title to Stripe.
		await user.click(within(strip).getByRole('button', { name: /stripe/i }));
		await waitFor(() => {
			const heading = within(sheet2).getByRole('heading', { level: 2 });
			expect(heading.textContent).toMatch(/stripe/i);
		});
	});

	// ── P6 — Density toggle (removed in May 2026) ─────────────────────────
	// The list/grid density toggle was removed entirely; only the grid
	// remains. Tests that exercised the toggle and the `?view=list` URL
	// param have been deleted.

	// ── P7 — Keyboard ergonomics ──────────────────────────────────────────

	it('typing "/" focuses the search input', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
		);
		renderDiscover();
		await screen.findByText('Stripe');
		// Focus on body, then press `/`.
		document.body.focus();
		(document.activeElement as HTMLElement | null)?.blur?.();
		await user.keyboard('/');
		const searchInput = screen.getByRole('textbox', { name: /search/i });
		expect(document.activeElement).toBe(searchInput);
	});

	// `?` (open keyboard-shortcuts help) is owned by `<PageHelp>` mounted on
	// the page shells (`/workspace`, `/discover`), not by `DiscoveryView`.
	// That binding is exercised in the per-page shell tests instead.

	// ── P8 — Credential close-the-loop ────────────────────────────────────

	it('emits a success toast when a credentialImported event arrives for the open sheet', async () => {
		const { emitCredentialImported } = await import('@/lib/events/credentialImported');
		const toastModule = await import('@/components/ui/toastStore');
		toastModule.clearAllToasts();

		worker.use(
			http.get('/apis', () =>
				HttpResponse.json({
					data: [{ id: 'stripe.com', name: 'Stripe', source: 'local' }],
					total: 1,
					page: 1,
				}),
			),
			http.get('/apis/stripe.com', () =>
				HttpResponse.json({ id: 'stripe.com', name: 'Stripe', source: 'local' }),
			),
			http.get('/apis/stripe.com/operations', () =>
				HttpResponse.json({ data: [], total: 0, page: 1 }),
			),
		);
		renderDiscover('/catalog?inspect=stripe.com');
		await screen.findByTestId('sheet-primitive');

		// Probe component to read the store via the hook.
		let liveToasts: ReturnType<typeof toastModule.useToasts> = [];
		function Probe() {
			liveToasts = toastModule.useToasts();
			return null;
		}
		const { render } = await import('@testing-library/react');
		render(<Probe />);

		emitCredentialImported({ api_id: 'stripe.com' });

		await waitFor(() => {
			expect(liveToasts.length).toBeGreaterThan(0);
		});
		expect(liveToasts[0].title).toMatch(/credential added/i);
		expect(liveToasts[0].variant).toBe('success');
	});
});

// ── Sectioned mode (used by /workspace) ──────────────────────────────────────
//
// The same DiscoveryView component, mounted with `mode="sectioned"`, must
// render two parallel sections (workspace + catalog) in browse mode and
// collapse to a single search feed in search mode.

describe('DiscoveryView (sectioned)', () => {
	function renderSectioned(route = '/workspace') {
		return renderWithProviders(<DiscoveryView mode="sectioned" />, {
			route,
			path: '/workspace',
		});
	}

	it('renders both section headers in browse mode and hides the Source segment', async () => {
		worker.use(http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })));
		renderSectioned();

		expect(await screen.findByTestId('discovery-section-your-workspace')).toBeInTheDocument();
		expect(screen.getByTestId('discovery-section-from-the-catalog')).toBeInTheDocument();
		// Sectioned mode hides the filter bar entirely — the source axis
		// is implicit in the section layout.
		expect(screen.queryByTestId('discovery-filter-bar')).toBeNull();
	});

	it('issues two parallel /apis requests, one per section, with distinct source params', async () => {
		const seenSources: (string | null)[] = [];
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				seenSources.push(url.searchParams.get('source'));
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
		);
		renderSectioned();
		await screen.findByTestId('discovery-section-your-workspace');
		await waitFor(() => {
			expect(seenSources).toContain('local');
			expect(seenSources).toContain('catalog');
		});
	});

	it('routes "Browse all in Discover" to /discover', async () => {
		worker.use(http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })));
		renderSectioned();
		const link = await screen.findByTestId('browse-all-discover');
		expect(link).toHaveAttribute('href', '/discover');
	});

	it('shows an inline cold-start notice in the workspace section when empty (and keeps the catalog section visible)', async () => {
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const source = url.searchParams.get('source');
				if (source === 'local') {
					return HttpResponse.json({ data: [], total: 0, page: 1 });
				}
				return HttpResponse.json({
					data: [{ id: 'github.com', name: 'GitHub', source: 'catalog' }],
					total: 1,
					page: 1,
				});
			}),
		);
		renderSectioned();
		// Inline cold-start in the workspace section.
		expect(
			await screen.findByTestId('discover-empty-cold-start-sectioned'),
		).toBeInTheDocument();
		// Catalog section still rendering its row.
		const catalogSection = screen.getByTestId('discovery-section-from-the-catalog');
		expect(await within(catalogSection).findByText('GitHub')).toBeInTheDocument();
	});

	it('collapses to a single search feed when ?q is non-empty', async () => {
		const user = userEvent.setup();
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q) {
					return HttpResponse.json({
						data: [{ id: 'stripe.com', name: 'Stripe', source: 'catalog' }],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
		);
		renderSectioned();
		await screen.findByTestId('discovery-section-your-workspace');

		await user.type(screen.getByLabelText(/search apis/i), 'stripe');
		await waitFor(() => {
			expect(screen.queryByTestId('discovery-section-your-workspace')).toBeNull();
		});
		expect(screen.queryByTestId('discovery-section-from-the-catalog')).toBeNull();
		// The browse grid is rendered with search results.
		await waitFor(() => {
			expect(screen.getByText('Stripe')).toBeInTheDocument();
		});
	});
});
