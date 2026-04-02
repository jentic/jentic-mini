import { http, HttpResponse, delay } from 'msw';
import { screen, renderWithProviders } from '../test-utils';
import { worker } from '../mocks/browser';
import WorkflowDetailPage from '@/pages/WorkflowDetailPage';

function renderWorkflow(slug = 'test~api') {
	return renderWithProviders(<WorkflowDetailPage />, {
		route: `/workflows/${slug}`,
		path: '/workflows/:slug',
	});
}

describe('WorkflowDetailPage', () => {
	it('renders loading state', async () => {
		worker.use(
			http.get('/workflows/:slug', async () => {
				await delay('infinite');
				return HttpResponse.json({});
			}),
		);

		renderWorkflow();

		expect(screen.getByText('Loading workflow...')).toBeInTheDocument();
	});

	it('renders workflow data when found', async () => {
		worker.use(
			http.get('/workflows/:slug', () =>
				HttpResponse.json({
					slug: 'test~api',
					name: 'Test Workflow',
					description: 'A test workflow',
					source: 'local',
					steps: [{ id: 's1', operation: 'getUser' }],
					involved_apis: ['test-api'],
				}),
			),
		);

		renderWorkflow();

		expect(await screen.findByText('Test Workflow')).toBeInTheDocument();
		expect(screen.getByText('A test workflow')).toBeInTheDocument();
		expect(screen.getByText('test~api')).toBeInTheDocument();
	});

	it('renders catalog fallback when workflow not found', async () => {
		worker.use(http.get('/workflows/:slug', () => HttpResponse.json(null, { status: 404 })));

		renderWorkflow();

		expect(await screen.findByText(/test\/api/)).toBeInTheDocument();
		expect(screen.getByText(/available in the Jentic public catalog/)).toBeInTheDocument();
	});

	it('renders error state for non-404 failures', async () => {
		worker.use(
			http.get('/workflows/:slug', () =>
				HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
			),
		);

		renderWorkflow();

		expect(await screen.findByText('Failed to load workflow')).toBeInTheDocument();
	});
});
