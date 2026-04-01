import { screen, waitFor, renderWithProviders, createErrorHandler } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import JobsPage from '../../pages/JobsPage'

describe('JobsPage', () => {
  it('renders the heading', async () => {
    renderWithProviders(<JobsPage />)
    expect(await screen.findByRole('heading', { name: /background jobs/i })).toBeInTheDocument()
  })

  it('shows empty state when no jobs exist', async () => {
    renderWithProviders(<JobsPage />)
    expect(await screen.findByText(/no jobs found/i)).toBeInTheDocument()
  })

  it('renders job table with populated data', async () => {
    worker.use(
      http.get('/jobs', () =>
        HttpResponse.json({
          items: [
            { id: 'job-1', kind: 'execute', status: 'complete', toolkit_id: 'tk-1', created_at: Math.floor(Date.now() / 1000) },
            { id: 'job-2', kind: 'workflow', status: 'running', toolkit_id: 'tk-2', created_at: Math.floor(Date.now() / 1000) - 120 },
          ],
          total: 2,
        }),
      ),
    )

    renderWithProviders(<JobsPage />)

    expect(await screen.findByText('job-1')).toBeInTheDocument()
    expect(screen.getByText('job-2')).toBeInTheDocument()
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBeGreaterThanOrEqual(3)
  })

  it('shows error state when API fails', async () => {
    worker.use(
      createErrorHandler('get', '/jobs', { status: 500 }),
    )

    renderWithProviders(<JobsPage />)

    expect(await screen.findByText(/failed to load jobs/i)).toBeInTheDocument()
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderWithProviders(<JobsPage />)
    await screen.findByRole('heading', { name: /background jobs/i })
    const results = await axe.run(container)
    const serious = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(serious).toEqual([])
  })
})
