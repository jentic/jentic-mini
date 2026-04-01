import { screen, waitFor, renderWithProviders, createErrorHandler } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import TracesPage from '../../pages/TracesPage'

describe('TracesPage', () => {
  it('renders the table with column headers', async () => {
    worker.use(
      http.get('/traces', () =>
        HttpResponse.json({
          traces: [{
            id: 't-1',
            toolkit_id: 'tk-1',
            operation_id: 'getUser',
            http_status: 200,
            duration_ms: 120,
            created_at: Math.floor(Date.now() / 1000) - 60,
          }],
          total: 1,
        }),
      ),
    )

    renderWithProviders(<TracesPage />)

    expect(await screen.findByText('Time')).toBeInTheDocument()
    expect(screen.getByText('Toolkit')).toBeInTheDocument()
    expect(screen.getByText('Operation / Workflow')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Duration')).toBeInTheDocument()
  })

  it('shows empty state when no traces exist', async () => {
    worker.use(
      http.get('/traces', () =>
        HttpResponse.json({ traces: [], total: 0 }),
      ),
    )

    renderWithProviders(<TracesPage />)

    expect(await screen.findByText('No traces found')).toBeInTheDocument()
    expect(screen.getByText(/Traces appear here when agents call the broker/)).toBeInTheDocument()
  })

  it('renders populated trace rows with different statuses', async () => {
    worker.use(
      http.get('/traces', () =>
        HttpResponse.json({
          traces: [
            {
              id: 't-1',
              toolkit_id: 'stripe-tk',
              operation_id: 'createCharge',
              http_status: 200,
              duration_ms: 95,
              created_at: Math.floor(Date.now() / 1000) - 30,
            },
            {
              id: 't-2',
              toolkit_id: 'github-tk',
              operation_id: 'listRepos',
              http_status: 404,
              duration_ms: 45,
              created_at: Math.floor(Date.now() / 1000) - 600,
            },
            {
              id: 't-3',
              toolkit_id: 'slack-tk',
              operation_id: null,
              workflow_id: 'send-notification',
              status: 'error',
              http_status: null,
              duration_ms: 3200,
              created_at: Math.floor(Date.now() / 1000) - 7200,
            },
          ],
          total: 3,
        }),
      ),
    )

    renderWithProviders(<TracesPage />)

    expect(await screen.findByText('stripe-tk')).toBeInTheDocument()
    expect(screen.getByText('createCharge')).toBeInTheDocument()
    expect(screen.getByText('95ms')).toBeInTheDocument()

    expect(screen.getByText('github-tk')).toBeInTheDocument()
    expect(screen.getByText('listRepos')).toBeInTheDocument()
    expect(screen.getByText('45ms')).toBeInTheDocument()

    expect(screen.getByText('slack-tk')).toBeInTheDocument()
    expect(screen.getByText('send-notification')).toBeInTheDocument()
    expect(screen.getByText('3200ms')).toBeInTheDocument()
  })

  it('shows error state when API returns 500', async () => {
    worker.use(
      createErrorHandler('get', '/traces', { status: 500 }),
    )

    renderWithProviders(<TracesPage />)

    expect(await screen.findByText('Failed to load traces')).toBeInTheDocument()
    expect(screen.getByText(/Please try refreshing the page/)).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = renderWithProviders(<TracesPage />)
    await screen.findByText('No traces found')
    const results = await axe.run(container)
    expect(results.violations).toEqual([])
  })
})
