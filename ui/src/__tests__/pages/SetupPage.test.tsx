import { http, HttpResponse, delay } from 'msw';
import axe from 'axe-core';
import { screen, renderWithProviders, userEvent } from '../test-utils';
import { worker } from '../mocks/browser';
import SetupPage from '@/pages/SetupPage';

describe('SetupPage — Step 1: Account creation', () => {
	it('renders the account creation form when setup is required', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'setup_required' })));

		renderWithProviders(<SetupPage />);

		expect(await screen.findByText(/create admin account/i)).toBeInTheDocument();
		expect(screen.getByText(/username/i)).toBeInTheDocument();
		expect(screen.getByText(/password/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
	});

	it('shows "Setup complete" when health is ok', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'ok' })));

		renderWithProviders(<SetupPage />);
		expect(await screen.findByText(/setup complete/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /go to dashboard/i })).toBeInTheDocument();
	});

	it('advances to key step after account creation', async () => {
		const user = userEvent.setup();

		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.post('/user/create', () => HttpResponse.json({ username: 'admin' })),
			http.post('/user/login', () => HttpResponse.json({ logged_in: true })),
		);

		renderWithProviders(<SetupPage />);

		await screen.findByText(/create admin account/i);
		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password123');
		await user.click(screen.getByRole('button', { name: /create account/i }));

		expect(await screen.findByText(/admin account created/i)).toBeInTheDocument();
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
			http.get('/health', () => HttpResponse.json({ status: 'account_required' })),
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

	it('shows generic error for non-409 failure', async () => {
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

		expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
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

describe('SetupPage — Step 2: Key generation', () => {
	async function advanceToKeyStep() {
		const user = userEvent.setup();

		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.post('/user/create', () => HttpResponse.json({ username: 'admin' })),
			http.post('/user/login', () => HttpResponse.json({ logged_in: true })),
		);

		const result = renderWithProviders(<SetupPage />);

		await screen.findByText(/create admin account/i);
		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password123');
		await user.click(screen.getByRole('button', { name: /create account/i }));

		await screen.findByText(/admin account created/i);
		return { user, ...result };
	}

	it('shows "Generate Agent API Key" button on key step', async () => {
		await advanceToKeyStep();

		expect(screen.getByRole('button', { name: /generate agent api key/i })).toBeInTheDocument();
	});

	it('shows "Generating..." while key is being created', async () => {
		worker.use(
			http.post('/default-api-key/generate', async () => {
				await delay(500);
				return HttpResponse.json({ key: 'jntc_test_key_abc123' });
			}),
		);

		const { user } = await advanceToKeyStep();

		await user.click(screen.getByRole('button', { name: /generate agent api key/i }));

		expect(await screen.findByRole('button', { name: /generating/i })).toBeDisabled();
	});

	it('displays the generated key and "Copy Key" button', async () => {
		const { user } = await advanceToKeyStep();

		await user.click(screen.getByRole('button', { name: /generate agent api key/i }));

		expect(await screen.findByText('jntc_test_key_abc123')).toBeInTheDocument();
		expect(screen.getByText(/will not be shown again/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /copy key/i })).toBeInTheDocument();
	});

	it('auto-advances when health shows account_created', async () => {
		worker.use(
			http.get('/health', () =>
				HttpResponse.json({ status: 'setup_required', account_created: true }),
			),
		);

		renderWithProviders(<SetupPage />);

		expect(await screen.findByText(/admin account created/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /generate agent api key/i })).toBeInTheDocument();
	});
});
