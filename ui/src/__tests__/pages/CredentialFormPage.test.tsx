import { http, HttpResponse } from 'msw';
import axe from 'axe-core';
import { screen, waitFor, renderWithProviders, userEvent, createErrorHandler } from '../test-utils';
import { worker } from '../mocks/browser';
import CredentialFormPage from '@/pages/CredentialFormPage';

describe('CredentialFormPage — create mode', () => {
	it('renders the heading and API picker', async () => {
		renderWithProviders(<CredentialFormPage />);

		expect(await screen.findByRole('heading', { name: /add credential/i })).toBeInTheDocument();
		expect(screen.getByPlaceholderText(/search apis/i)).toBeInTheDocument();
	});

	it('shows the empty state prompt', async () => {
		renderWithProviders(<CredentialFormPage />);

		expect(await screen.findByText(/start typing to search/i)).toBeInTheDocument();
	});

	it('shows search results when user types', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q?.includes('stripe')) {
					return HttpResponse.json({
						data: [
							{
								id: 'stripe',
								name: 'Stripe',
								description: 'Payment processing',
								source: 'local',
							},
						],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
		);

		renderWithProviders(<CredentialFormPage />);

		const input = await screen.findByPlaceholderText(/search apis/i);
		await user.type(input, 'stripe');

		expect(await screen.findByText('Stripe')).toBeInTheDocument();
	});

	it('shows "no APIs found" for empty search results', async () => {
		const user = userEvent.setup();

		worker.use(http.get('/apis', () => HttpResponse.json({ data: [], total: 0, page: 1 })));

		renderWithProviders(<CredentialFormPage />);

		const input = await screen.findByPlaceholderText(/search apis/i);
		await user.type(input, 'nonexistent');

		expect(await screen.findByText(/no apis found/i)).toBeInTheDocument();
	});

	it('advances to credential form after selecting an API', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q?.includes('stripe')) {
					return HttpResponse.json({
						data: [
							{
								id: 'stripe',
								name: 'Stripe',
								description: 'Payments',
								source: 'local',
							},
						],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
			http.get('/apis/:id', () =>
				HttpResponse.json({
					id: 'stripe',
					name: 'Stripe',
					source: 'local',
					security_schemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
				}),
			),
		);

		renderWithProviders(<CredentialFormPage />);

		const input = await screen.findByPlaceholderText(/search apis/i);
		await user.type(input, 'stripe');

		const apiRow = await screen.findByText('Stripe');
		await user.click(apiRow);

		expect(await screen.findByText(/bearer token/i)).toBeInTheDocument();
	});

	it('has no accessibility violations', async () => {
		const { container } = renderWithProviders(<CredentialFormPage />);
		await screen.findByRole('heading', { name: /add credential/i });
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});

describe('CredentialFormPage — edit mode', () => {
	it('renders "Edit Credential" heading in edit mode', async () => {
		worker.use(
			http.get('/credentials/:id', () =>
				HttpResponse.json({
					id: 'cred-1',
					label: 'My Token',
					api_id: 'stripe',
					auth_type: 'bearer',
				}),
			),
			http.get('/apis/stripe', () =>
				HttpResponse.json({
					id: 'stripe',
					name: 'Stripe',
					source: 'local',
					security_schemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
				}),
			),
		);

		renderWithProviders(<CredentialFormPage />, {
			route: '/credentials/cred-1/edit',
			path: '/credentials/:id/edit',
		});

		expect(
			await screen.findByRole('heading', { name: /edit credential/i }),
		).toBeInTheDocument();
	});

	it('pre-fills the credential fields in edit mode', async () => {
		worker.use(
			http.get('/credentials/:id', () =>
				HttpResponse.json({
					id: 'cred-1',
					label: 'My Stripe Token',
					api_id: 'stripe',
					auth_type: 'bearer',
					value: 'sk_test_xxxx',
				}),
			),
			http.get('/apis/stripe', () =>
				HttpResponse.json({
					id: 'stripe',
					name: 'Stripe',
					source: 'local',
					security_schemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
				}),
			),
		);

		renderWithProviders(<CredentialFormPage />, {
			route: '/credentials/cred-1/edit',
			path: '/credentials/:id/edit',
		});

		expect(
			await screen.findByRole('heading', { name: /edit credential/i }),
		).toBeInTheDocument();
		// The form should show the bearer token field
		expect(await screen.findByText(/bearer token/i)).toBeInTheDocument();
	});
});

describe('CredentialFormPage — OAuth connect link', () => {
	async function navigateToOAuth2Api(user: ReturnType<typeof userEvent.setup>) {
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q?.includes('google')) {
					return HttpResponse.json({
						data: [
							{
								id: 'googleapis.com/calendar',
								name: 'Google Calendar',
								description: 'Calendar API',
								source: 'local',
							},
						],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
			http.get('/apis/:id', () =>
				HttpResponse.json({
					id: 'googleapis.com/calendar',
					name: 'Google Calendar',
					source: 'local',
					security_schemes: { oauth2: { type: 'oauth2' } },
				}),
			),
			http.get('/oauth-brokers', () =>
				HttpResponse.json([{ id: 'pipedream', type: 'pipedream', config: {} }]),
			),
		);

		renderWithProviders(<CredentialFormPage />);

		const input = await screen.findByPlaceholderText(/search apis/i);
		await user.type(input, 'google');
		await user.click(await screen.findByText('Google Calendar'));
	}

	it('disables Create Connect Link button when label is empty', async () => {
		const user = userEvent.setup();
		await navigateToOAuth2Api(user);

		await screen.findByText(/connect via oauth/i);

		// Clear the pre-filled label
		const labelInput = screen.getByLabelText(/label/i);
		await user.clear(labelInput);

		const connectButton = screen.getByRole('button', { name: /create connect link/i });
		expect(connectButton).toBeDisabled();
	});

	it('shows connect link after successful generation', async () => {
		const user = userEvent.setup();

		worker.use(
			http.post('/oauth-brokers/:id/connect-link', () =>
				HttpResponse.json({
					connect_link_url:
						'https://pipedream.com/_static/connect.html?token=test&app=google_calendar',
					expires_at: Date.now() / 1000 + 3600,
					broker_id: 'pipedream',
					app: 'google_calendar',
				}),
			),
		);

		await navigateToOAuth2Api(user);
		await screen.findByText(/connect via oauth/i);

		const connectButton = screen.getByRole('button', { name: /create connect link/i });
		await user.click(connectButton);

		expect(await screen.findByText(/open connect link/i)).toBeInTheDocument();
	});

	it('enables Create Connect Link button when label is provided', async () => {
		const user = userEvent.setup();
		await navigateToOAuth2Api(user);

		await screen.findByText(/connect via oauth/i);

		const labelInput = screen.getByLabelText(/label/i);
		await user.clear(labelInput);
		await user.type(labelInput, 'Work Cal');

		const connectButton = screen.getByRole('button', { name: /create connect link/i });
		expect(connectButton).toBeEnabled();
	});
});

describe('CredentialFormPage — mutation errors', () => {
	async function fillAndSubmitCredential(user: ReturnType<typeof userEvent.setup>) {
		worker.use(
			http.get('/apis', ({ request }) => {
				const url = new URL(request.url);
				const q = url.searchParams.get('q');
				if (q?.includes('stripe')) {
					return HttpResponse.json({
						data: [
							{
								id: 'stripe',
								name: 'Stripe',
								description: 'Payments',
								source: 'local',
							},
						],
						total: 1,
						page: 1,
					});
				}
				return HttpResponse.json({ data: [], total: 0, page: 1 });
			}),
			http.get('/apis/:id', () =>
				HttpResponse.json({
					id: 'stripe',
					name: 'Stripe',
					source: 'local',
					security_schemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
				}),
			),
		);

		renderWithProviders(<CredentialFormPage />);

		const input = await screen.findByPlaceholderText(/search apis/i);
		await user.type(input, 'stripe');
		await user.click(await screen.findByText('Stripe'));

		await screen.findByText(/bearer token/i);

		const tokenField = screen.getByPlaceholderText(/paste your token/i);
		await user.type(tokenField, 'sk_test_123');

		await user.click(screen.getByRole('button', { name: /save credential/i }));
	}

	it('shows error on network failure when creating a credential', async () => {
		const user = userEvent.setup();

		worker.use(createErrorHandler('post', '/credentials', { networkError: true }));

		await fillAndSubmitCredential(user);

		await waitFor(() => {
			expect(screen.getByRole('alert')).toBeInTheDocument();
		});
	});

	it('shows error on server 500 when creating a credential', async () => {
		const user = userEvent.setup();

		worker.use(createErrorHandler('post', '/credentials', { status: 500 }));

		await fillAndSubmitCredential(user);

		await waitFor(() => {
			expect(screen.getByRole('alert')).toBeInTheDocument();
		});
	});
});
