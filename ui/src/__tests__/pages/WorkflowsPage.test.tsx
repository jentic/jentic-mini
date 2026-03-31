import { screen, waitFor, renderWithProviders, createErrorHandler } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import WorkflowsPage from '../../pages/WorkflowsPage'

describe('WorkflowsPage', () => {
  it('renders the heading', async () => {
    renderWithProviders(<WorkflowsPage />)
    expect(await screen.findByRole('heading', { name: /workflows/i })).toBeInTheDocument()
  })

  it('shows empty state when no workflows exist', async () => {
    renderWithProviders(<WorkflowsPage />)
    expect(await screen.findByText(/no workflows registered/i)).toBeInTheDocument()
  })

  it('renders workflow list with populated data', async () => {
    worker.use(
      http.get('/workflows', () =>
        HttpResponse.json([
          { slug: 'summarise-discourse', name: 'Summarise Discourse Topics', description: 'Summarises recent topics', source: 'local', steps_count: 3, involved_apis: ['discourse-api'] },
          { slug: 'sync-contacts', name: 'Sync Contacts', description: 'Sync CRM contacts', source: 'catalog', steps_count: 5, involved_apis: ['salesforce', 'hubspot'] },
        ]),
      ),
    )

    renderWithProviders(<WorkflowsPage />)

    expect(await screen.findByText('Summarise Discourse Topics')).toBeInTheDocument()
    expect(screen.getByText('Sync Contacts')).toBeInTheDocument()
    expect(screen.getByText('3 steps')).toBeInTheDocument()
    expect(screen.getByText('5 steps')).toBeInTheDocument()
  })

  it('shows error state when API fails', async () => {
    worker.use(
      createErrorHandler('get', '/workflows', { status: 500 }),
    )

    renderWithProviders(<WorkflowsPage />)

    expect(await screen.findByText(/failed to load workflows/i)).toBeInTheDocument()
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderWithProviders(<WorkflowsPage />)
    await screen.findByRole('heading', { name: /workflows/i })
    const results = await axe.run(container)
    const serious = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(serious).toEqual([])
  })
})
