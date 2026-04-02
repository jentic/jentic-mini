import { delay, http, HttpResponse } from 'msw';
import axe from 'axe-core';
import { screen, renderWithProviders, userEvent } from '../test-utils';
import { worker } from '../mocks/browser';
import LoginPage from '@/pages/LoginPage';

describe('LoginPage', () => {
	it('renders the login form', () => {
		renderWithProviders(<LoginPage />);
		expect(screen.getByLabelText('Username')).toBeInTheDocument();
		expect(screen.getByLabelText('Password')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
	});

	it('shows "Logging in..." while submitting', async () => {
		const user = userEvent.setup();

		worker.use(
			http.post('/user/login', async () => {
				await delay('infinite');
				return HttpResponse.json({ logged_in: true });
			}),
		);

		renderWithProviders(<LoginPage />);

		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password');
		await user.click(screen.getByRole('button', { name: /log in/i }));

		expect(await screen.findByRole('button', { name: /logging in/i })).toBeDisabled();
	});

	it('shows error message on failed login (401)', async () => {
		const user = userEvent.setup();

		worker.use(
			http.post('/user/login', () =>
				HttpResponse.json({ error: 'bad credentials' }, { status: 401 }),
			),
		);

		renderWithProviders(<LoginPage />);

		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'wrong');
		await user.click(screen.getByRole('button', { name: /log in/i }));

		expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
	});

	it('shows error message on network error (non-401)', async () => {
		const user = userEvent.setup();

		worker.use(
			http.post('/user/login', () =>
				HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
			),
		);

		renderWithProviders(<LoginPage />);

		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password');
		await user.click(screen.getByRole('button', { name: /log in/i }));

		expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
	});

	it('calls the login API on form submission and enters pending state', async () => {
		const user = userEvent.setup();

		let loginCalled = false;
		worker.use(
			http.post('/user/login', async () => {
				loginCalled = true;
				await delay('infinite');
				return HttpResponse.json({ logged_in: true, username: 'admin' });
			}),
		);

		renderWithProviders(<LoginPage />);

		await user.type(screen.getByLabelText('Username'), 'admin');
		await user.type(screen.getByLabelText('Password'), 'password');
		await user.click(screen.getByRole('button', { name: /log in/i }));

		expect(await screen.findByRole('button', { name: /logging in/i })).toBeDisabled();
		expect(loginCalled).toBe(true);
	});

	it('has no critical accessibility violations', async () => {
		const { container } = renderWithProviders(<LoginPage />);
		const results = await axe.run(container);
		const critical = results.violations.filter(
			(v) => v.impact === 'critical' || v.impact === 'serious',
		);
		expect(critical).toEqual([]);
	});
});
