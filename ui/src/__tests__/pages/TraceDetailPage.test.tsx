import { http, HttpResponse, delay } from 'msw';
import { screen, renderWithProviders } from '../test-utils';
import { worker } from '../mocks/browser';
import TraceDetailPage from '@/pages/TraceDetailPage';

function renderTrace(id = 'trace-123') {
	return renderWithProviders(<TraceDetailPage />, {
		route: `/traces/${id}`,
		path: '/traces/:id',
	});
}

describe('TraceDetailPage', () => {
	it('renders loading state', async () => {
		worker.use(
			http.get('/traces/:traceId', async () => {
				await delay('infinite');
				return HttpResponse.json({});
			}),
		);

		renderTrace();

		expect(screen.getByText('Loading trace...')).toBeInTheDocument();
	});

	it('renders trace details when found', async () => {
		worker.use(
			http.get('/traces/:traceId', () =>
				HttpResponse.json({
					id: 'trace-123',
					toolkit_id: 'tk-1',
					operation_id: 'getUser',
					http_status: 200,
					duration_ms: 150,
					created_at: 1700000000,
				}),
			),
		);

		renderTrace();

		expect(await screen.findByText('trace-123')).toBeInTheDocument();
		expect(screen.getByText('tk-1')).toBeInTheDocument();
		expect(screen.getByText('getUser')).toBeInTheDocument();
		expect(screen.getByText('150ms')).toBeInTheDocument();
		expect(screen.getByText('Summary')).toBeInTheDocument();
	});

	it('renders "not found" when trace is null', async () => {
		worker.use(http.get('/traces/:traceId', () => HttpResponse.json(null, { status: 404 })));

		renderTrace();

		expect(await screen.findByText('Trace not found.')).toBeInTheDocument();
		expect(screen.getByText('Back to Traces')).toBeInTheDocument();
	});
});
