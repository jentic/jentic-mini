import { http, HttpResponse } from 'msw';
import { Routes, Route } from 'react-router-dom';
import { screen, renderWithProviders } from '../test-utils';
import { worker } from '../mocks/browser';
import { Layout } from '@/components/layout/Layout';

function renderLayout(route = '/') {
	return renderWithProviders(
		<Routes>
			<Route element={<Layout />}>
				<Route path="/" element={<div>Dashboard</div>} />
				<Route path="/toolkits" element={<div>Toolkits</div>} />
			</Route>
		</Routes>,
		{ route },
	);
}

describe('Layout', () => {
	it('renders sidebar navigation links', async () => {
		renderLayout();

		await screen.findByText('admin');
		const nav = document.querySelector('nav')!;
		expect(nav).toBeInTheDocument();
		expect(nav.textContent).toContain('Dashboard');
		expect(nav.textContent).toContain('Search');
		expect(nav.textContent).toContain('API Catalog');
		expect(nav.textContent).toContain('Workflows');
		expect(nav.textContent).toContain('Toolkits');
		expect(nav.textContent).toContain('Credentials');
		expect(nav.textContent).toContain('Traces');
	});

	it('renders username in header when authenticated', async () => {
		renderLayout();

		expect(await screen.findByText('admin')).toBeInTheDocument();
	});

	it('renders logout button', async () => {
		renderLayout();

		expect(await screen.findByText('Logout')).toBeInTheDocument();
	});

	it('renders child route content via Outlet', async () => {
		renderLayout('/toolkits');

		await screen.findByText('admin');
		const main = document.querySelector('main')!;
		expect(main.textContent).toContain('Toolkits');
	});

	it('shows pending requests badge when there are pending requests', async () => {
		worker.use(
			http.get('/toolkits', () => HttpResponse.json([{ id: 'tk-1', name: 'Toolkit A' }])),
			http.get('/toolkits/tk-1/access-requests', () =>
				HttpResponse.json([{ id: 'req-1', status: 'pending', reason: 'Need access' }]),
			),
		);

		renderLayout();

		expect(await screen.findByText(/1 Pending Request/)).toBeInTheDocument();
	});

	it('shows update available banner when new version exists', async () => {
		worker.use(
			http.get('/version', () =>
				HttpResponse.json({
					current: '0.2.0',
					latest: '0.3.0',
					release_url: 'https://github.com/release/0.3.0',
				}),
			),
		);

		renderLayout();

		expect(await screen.findByText(/Update available: 0.3.0/)).toBeInTheDocument();
	});

	it('renders the Jentic logo', async () => {
		renderLayout();

		await screen.findByText('admin');
		expect(screen.getAllByText('Mini').length).toBeGreaterThan(0);
	});
});
