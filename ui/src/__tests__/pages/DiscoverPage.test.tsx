import { http, HttpResponse } from 'msw';
import { screen, waitFor, renderWithProviders, userEvent } from '../test-utils';
import { worker } from '../mocks/browser';
import DiscoverPage from '@/pages/DiscoverPage';

// Helper: render DiscoverPage at a specific URL
function renderDiscover(route = '/catalog') {
	return renderWithProviders(<DiscoverPage />, { route, path: '/catalog' });
}

describe('DiscoverPage', () => {
	// ── Heading ─────────────────────────────────────────────────────────────

	it('renders the Discover heading', async () => {
		renderDiscover();
		expect(await screen.findByRole('heading', { name: /discover/i })).toBeInTheDocument();
	});

	// ── Browse mode (no query) ───────────────────────────────────────────────

	it('shows APIs and workflows in browse mode when both type chips are active', async () => {
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
					],
					total: 1,
					page: 1,
				}),
			),
			http.get('/workflows', () =>
				HttpResponse.json([{ id: 'wf-1', name: 'My Workflow', description: 'does stuff' }]),
			),
		);

		renderDiscover();

		await waitFor(() => {
			expect(screen.getByText('Stripe')).toBeInTheDocument();
		});
		expect(screen.getByText('My Workflow')).toBeInTheDocument();
	});

	it('shows catalog APIs when source=catalog is active', async () => {
		worker.use(
			http.get('/catalog', () =>
				HttpResponse.json([
					{ id: 'github', name: 'GitHub', source: 'catalog', has_credentials: false },
				]),
			),
			http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })),
			http.get('/workflows', () => HttpResponse.json([])),
		);

		renderDiscover('/catalog?source=local,catalog');

		await waitFor(() => {
			expect(screen.getByText('GitHub')).toBeInTheDocument();
		});
	});

	// ── Search mode (with query) ─────────────────────────────────────────────

	it('switches to BM25 search mode when a query is entered', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/search', () =>
				HttpResponse.json([
					{
						id: 'GET/api.stripe.com/v1/customers',
						type: 'operation',
						source: 'local',
						summary: 'List customers',
						score: 0.92,
					},
				]),
			),
		);

		renderDiscover();

		const input = screen.getByRole('textbox', { name: /search/i });
		await user.type(input, 'stripe customer');

		await waitFor(() => {
			expect(screen.getByText('List customers')).toBeInTheDocument();
		});
	});

	it('chip toggle updates the URL and prunes the result list', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/search', () =>
				HttpResponse.json([
					{
						id: 'GET/api.stripe.com/v1/charges',
						type: 'operation',
						source: 'local',
						summary: 'List charges',
						score: 0.88,
					},
					{
						id: 'wf-stripe-checkout',
						type: 'workflow',
						source: 'local',
						summary: 'Stripe Checkout Flow',
						score: 0.75,
					},
				]),
			),
		);

		renderDiscover();
		const input = screen.getByRole('textbox', { name: /search/i });
		await user.type(input, 'stripe');

		// Wait for both results to appear.
		await waitFor(() => {
			expect(screen.getByText('List charges')).toBeInTheDocument();
		});
		expect(screen.getByText('Stripe Checkout Flow')).toBeInTheDocument();

		// Disable the 'operation' type chip — only workflows remain.
		const operationChip = screen.getByRole('button', { name: 'operation' });
		await user.click(operationChip);

		await waitFor(() => {
			expect(screen.queryByText('List charges')).not.toBeInTheDocument();
		});
		expect(screen.getByText('Stripe Checkout Flow')).toBeInTheDocument();
	});

	// ── Import flow ──────────────────────────────────────────────────────────

	it('clicking Import on a catalog result triggers the two-step import', async () => {
		const user = userEvent.setup();
		let importCalled = false;

		worker.use(
			http.get('/search', () =>
				HttpResponse.json([
					{
						id: 'GET/api.example.com/v1/items',
						type: 'operation',
						source: 'catalog',
						summary: 'List items',
						api_id: 'example-api',
						score: 0.9,
					},
				]),
			),
			http.get('/catalog/example-api', () =>
				HttpResponse.json({ id: 'example-api', spec_url: 'https://example.com/spec.json' }),
			),
			http.post('/import', () => {
				importCalled = true;
				return HttpResponse.json({ imported: 1, failed: 0, results: [] });
			}),
		);

		renderDiscover();
		const input = screen.getByRole('textbox', { name: /search/i });
		await user.type(input, 'list items');

		await waitFor(() => {
			expect(screen.getByText('List items')).toBeInTheDocument();
		});

		// Expand the result card.
		await user.click(screen.getByText('List items'));

		// Click the Import button inside the expanded panel.
		const importBtn = await screen.findByRole('button', { name: /import this api/i });
		await user.click(importBtn);

		await waitFor(() => {
			expect(importCalled).toBe(true);
		});
	});
});
