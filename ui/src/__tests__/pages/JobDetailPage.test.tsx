import { http, HttpResponse, delay } from 'msw';
import { screen, renderWithProviders } from '../test-utils';
import { worker } from '../mocks/browser';
import JobDetailPage from '@/pages/JobDetailPage';

function renderJob(id = 'job-456') {
	return renderWithProviders(<JobDetailPage />, {
		route: `/jobs/${id}`,
		path: '/jobs/:id',
	});
}

describe('JobDetailPage', () => {
	it('renders loading state', async () => {
		worker.use(
			http.get('/jobs/:jobId', async () => {
				await delay('infinite');
				return HttpResponse.json({});
			}),
		);

		renderJob();

		expect(screen.getByText('Loading job...')).toBeInTheDocument();
	});

	it('renders job details when found', async () => {
		worker.use(
			http.get('/jobs/:jobId', () =>
				HttpResponse.json({
					id: 'job-456',
					status: 'running',
					kind: 'execute',
					toolkit_id: 'tk-1',
					created_at: 1700000000,
				}),
			),
		);

		renderJob();

		expect(await screen.findByText('job-456')).toBeInTheDocument();
		expect(screen.getByText('running')).toBeInTheDocument();
		expect(screen.getByText('execute')).toBeInTheDocument();
		expect(screen.getByText('tk-1')).toBeInTheDocument();
		expect(screen.getByText('Summary')).toBeInTheDocument();
	});

	it('shows cancel button for running jobs', async () => {
		worker.use(
			http.get('/jobs/:jobId', () =>
				HttpResponse.json({
					id: 'job-456',
					status: 'running',
					kind: 'execute',
					created_at: 1700000000,
				}),
			),
		);

		renderJob();

		expect(await screen.findByRole('button', { name: /cancel job/i })).toBeInTheDocument();
	});

	it('renders "not found" when job is null', async () => {
		worker.use(http.get('/jobs/:jobId', () => HttpResponse.json(null, { status: 404 })));

		renderJob();

		expect(await screen.findByText('Job not found.')).toBeInTheDocument();
		expect(screen.getByText('Back to Jobs')).toBeInTheDocument();
	});
});
