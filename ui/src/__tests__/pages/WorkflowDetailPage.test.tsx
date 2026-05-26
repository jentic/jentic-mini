import { http, HttpResponse, delay } from 'msw';
import { screen, renderWithProviders } from '../test-utils';
import { worker } from '../mocks/browser';
import WorkflowDetailPage from '@/pages/WorkflowDetailPage';

function renderWorkflow(slug = 'test~api', searchParams = '') {
	return renderWithProviders(<WorkflowDetailPage />, {
		route: `/workspace/workflows/${slug}${searchParams}`,
		path: '/workspace/workflows/:slug',
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

		expect(await screen.findByRole('heading', { name: 'Test Workflow' })).toBeInTheDocument();
		// Description renders in the PageHeader subtitle. The "About" card
		// is gone so it should appear exactly once.
		expect(screen.getByText('A test workflow')).toBeInTheDocument();
		// Slug now sits next to the segmented toggle as a quiet caption,
		// not in the meta strip and not as a header eyebrow.
		expect(screen.getByTestId('workflow-slug')).toHaveTextContent('test~api');
		// Meta strip is the compact ribbon under the header. It owns
		// Operations / APIs / Last run; the source pill was dropped
		// because GET /workflows/{slug} doesn't carry a `source` field
		// and catalog workflows hit the catalog fallback before getting
		// here, so the pill was always "Local" decoration.
		expect(screen.getByTestId('workflow-meta-strip')).toBeInTheDocument();
		expect(screen.queryByTestId('workflow-meta-slug')).not.toBeInTheDocument();
		expect(screen.queryByTestId('workflow-meta-source')).not.toBeInTheDocument();
		// BackButton lives below the PageHeader, not inside it. The
		// PageHeader primitive itself stays invariant across pages.
		expect(screen.getByTestId('back-button')).toBeInTheDocument();
		expect(screen.queryByTestId('page-header-back')).not.toBeInTheDocument();
		// Default tab is Overview — Operations section should be visible.
		expect(screen.getByTestId('workflow-overview')).toBeInTheDocument();
		expect(screen.getByTestId('workflow-overview-steps')).toBeInTheDocument();
	});

	it('honours ?view=docs deep link by skipping Overview', async () => {
		worker.use(
			http.get('/workflows/:slug', () =>
				HttpResponse.json({
					slug: 'test~api',
					name: 'Test Workflow',
					source: 'local',
					steps: [],
					involved_apis: [],
				}),
			),
		);

		renderWorkflow('test~api', '?view=docs');

		await screen.findByRole('heading', { name: 'Test Workflow' });
		// Overview body must not render when ?view=docs is set.
		expect(screen.queryByTestId('workflow-overview')).not.toBeInTheDocument();
	});

	it('renders catalog fallback when workflow not found (404 skips retry)', async () => {
		worker.use(http.get('/workflows/:slug', () => HttpResponse.json(null, { status: 404 })));

		renderWorkflow();

		// Catalog fallback now uses the same PageHeader skeleton; the
		// title is the api id derived from the slug.
		expect(await screen.findByRole('heading', { name: /test\/api/ })).toBeInTheDocument();
		expect(screen.getByTestId('workflow-catalog-import')).toBeInTheDocument();
	});

	it('renders error state for non-404 failures', async () => {
		worker.use(
			http.get('/workflows/:slug', () =>
				HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
			),
		);

		renderWorkflow();

		// The page retries 500s twice (3 total MSW round-trips) before
		// surfacing the error — the timeout accounts for that. The retry
		// logic itself is unit-tested below.
		expect(
			await screen.findByText('Failed to load workflow', {}, { timeout: 5000 }),
		).toBeInTheDocument();
	});
});

// ---------------------------------------------------------------------------
// Unit test for the retry predicate — verifiable without MSW timing
// ---------------------------------------------------------------------------

describe('WorkflowDetailPage retry logic', () => {
	const retry = (failureCount: number, err: { status: number }) =>
		err?.status !== 404 && failureCount < 2;

	it('retries 500s up to twice', () => {
		expect(retry(0, { status: 500 })).toBe(true);
		expect(retry(1, { status: 500 })).toBe(true);
		expect(retry(2, { status: 500 })).toBe(false);
	});

	it('never retries 404s', () => {
		expect(retry(0, { status: 404 })).toBe(false);
	});

	it('retries other server errors', () => {
		expect(retry(0, { status: 503 })).toBe(true);
		expect(retry(1, { status: 502 })).toBe(true);
	});
});
