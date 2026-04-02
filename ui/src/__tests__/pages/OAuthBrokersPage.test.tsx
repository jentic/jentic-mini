import { http, HttpResponse } from 'msw';
import axe from 'axe-core';
import { screen, waitFor, renderWithProviders, userEvent, createErrorHandler } from '../test-utils';
import { worker } from '../mocks/browser';
import OAuthBrokersPage from '@/pages/OAuthBrokersPage';

describe('OAuthBrokersPage', () => {
	it('renders the heading', async () => {
		renderWithProviders(<OAuthBrokersPage />);
		expect(await screen.findByRole('heading', { name: /oauth brokers/i })).toBeInTheDocument();
	});

	it('shows empty state when no brokers configured', async () => {
		renderWithProviders(<OAuthBrokersPage />);
		expect(await screen.findByText(/no oauth brokers configured/i)).toBeInTheDocument();
		expect(screen.getByText(/add your first broker/i)).toBeInTheDocument();
	});

	it('renders broker cards with populated data', async () => {
		worker.use(
			http.get('/oauth-brokers', () =>
				HttpResponse.json([
					{
						id: 'pipedream-1',
						type: 'pipedream',
						config: { project_id: 'proj-abc', default_external_user_id: 'default' },
						created_at: String(Math.floor(Date.now() / 1000)),
					},
					{
						id: 'pipedream-2',
						type: 'pipedream',
						config: { project_id: 'proj-xyz', default_external_user_id: 'agent-1' },
						created_at: String(Math.floor(Date.now() / 1000)),
					},
				]),
			),
		);

		renderWithProviders(<OAuthBrokersPage />);

		expect(await screen.findByText('pipedream-1')).toBeInTheDocument();
		expect(screen.getByText('pipedream-2')).toBeInTheDocument();
		expect(screen.getByText('project: proj-abc')).toBeInTheDocument();
		expect(screen.getByText('project: proj-xyz')).toBeInTheDocument();
	});

	it('opens add broker form on button click', async () => {
		const user = userEvent.setup();
		renderWithProviders(<OAuthBrokersPage />);

		await screen.findByRole('heading', { name: /oauth brokers/i });
		await user.click(screen.getByRole('button', { name: /add broker/i }));

		expect(await screen.findByText(/add oauth broker/i)).toBeInTheDocument();
		expect(screen.getByLabelText(/broker id/i)).toBeInTheDocument();
		expect(screen.getByLabelText(/client id/i)).toBeInTheDocument();
	});

	it('submits add broker form successfully', async () => {
		const user = userEvent.setup();
		renderWithProviders(<OAuthBrokersPage />);

		await screen.findByRole('heading', { name: /oauth brokers/i });
		await user.click(screen.getByRole('button', { name: /add broker/i }));

		await user.type(screen.getByLabelText(/broker id/i), 'my-broker');
		await user.type(screen.getByLabelText(/client id/i), 'client-123');
		await user.type(screen.getByLabelText(/client secret/i), 'secret-456');
		await user.type(screen.getByLabelText(/project id/i), 'proj-789');

		await user.click(screen.getByRole('button', { name: /create broker/i }));

		await waitFor(() => {
			expect(screen.queryByText(/add oauth broker/i)).not.toBeInTheDocument();
		});
	});

	it('shows error on failed broker creation', async () => {
		worker.use(
			createErrorHandler('post', '/oauth-brokers', {
				status: 500,
				body: { detail: 'Server error' },
			}),
		);

		const user = userEvent.setup();
		renderWithProviders(<OAuthBrokersPage />);

		await screen.findByRole('heading', { name: /oauth brokers/i });
		await user.click(screen.getByRole('button', { name: /add broker/i }));

		await user.type(screen.getByLabelText(/broker id/i), 'bad-broker');
		await user.type(screen.getByLabelText(/client id/i), 'client-fail');
		await user.type(screen.getByLabelText(/client secret/i), 'secret-fail');
		await user.type(screen.getByLabelText(/project id/i), 'proj-fail');

		await user.click(screen.getByRole('button', { name: /create broker/i }));

		expect(await screen.findByRole('alert')).toBeInTheDocument();
	});

	it('has no critical accessibility violations', async () => {
		const { container } = renderWithProviders(<OAuthBrokersPage />);
		await screen.findByRole('heading', { name: /oauth brokers/i });
		const results = await axe.run(container);
		const serious = results.violations.filter(
			(v) => v.impact === 'critical' || v.impact === 'serious',
		);
		expect(serious).toEqual([]);
	});
});
