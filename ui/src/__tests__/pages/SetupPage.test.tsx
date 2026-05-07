import { http, HttpResponse, delay } from 'msw';
import axe from 'axe-core';
import { screen, renderWithProviders, userEvent } from '../test-utils';
import { worker } from '../mocks/browser';
import SetupPage from '@/pages/SetupPage';

describe('SetupPage — Account creation', () => {
	it('renders the account creation form when setup is required', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'setup_required' })));

		renderWithProviders(<SetupPage />);

		expect(await screen.findByText(/create admin account/i)).toBeInTheDocument();
		expect(screen.getByText(/username/i)).toBeInTheDocument();
		expect(screen.getByText(/password/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
	});

	it('shows admin-focused setup copy (not agent OAuth URLs)', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'setup_required' })));

		renderWithProviders(<SetupPage />);

		expect(
			await screen.findByText(/create your administrator account below/i),
		).toBeInTheDocument();
		expect(screen.getByText(/agents register themselves afterward/i)).toBeInTheDocument();
		expect(screen.queryByText(/metadata:/i)).not.toBeInTheDocument();
	});

	it('shows "Setup complete" when health is ok', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'ok' })));

		renderWithProviders(<SetupPage />);
		expect(await screen.findByText(/setup complete/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /go to dashboard/i })).toBeInTheDocument();
	});

	it('shows "Creating..." while submitting account', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.post('/user/create', async () => {
				await delay(500);
				return HttpResponse.json({ username: 'admin' });
			}),
		);

		renderWithProviders(<SetupPage />);

		await screen.findByText(/create admin account/i);
		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password123');
		await user.click(screen.getByRole('button', { name: /create account/i }));

		expect(await screen.findByRole('button', { name: /creating/i })).toBeDisabled();
	});

	it('shows warning when account already exists (409)', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.post('/user/create', () =>
				HttpResponse.json({ detail: 'already exists' }, { status: 409 }),
			),
		);

		renderWithProviders(<SetupPage />);

		await screen.findByText(/create admin account/i);
		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'pass');
		await user.click(screen.getByRole('button', { name: /create account/i }));

		expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
	});

	it('surfaces the server error message for non-409 failure', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.post('/user/create', () =>
				HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
			),
		);

		renderWithProviders(<SetupPage />);

		await screen.findByText(/create admin account/i);
		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'pass');
		await user.click(screen.getByRole('button', { name: /create account/i }));

		expect(await screen.findByText(/internal server error/i)).toBeInTheDocument();
	});

	it('has no critical accessibility violations', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'setup_required' })));

		const { container } = renderWithProviders(<SetupPage />);
		await screen.findByText(/create admin account/i);
		const results = await axe.run(container);
		const critical = results.violations.filter(
			(v) => v.impact === 'critical' || v.impact === 'serious',
		);
		expect(critical).toEqual([]);
	});
});
