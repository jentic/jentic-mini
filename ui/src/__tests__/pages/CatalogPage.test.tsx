import { screen, waitFor, renderWithProviders, userEvent, createErrorHandler } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import CatalogPage from '../../pages/CatalogPage'

describe('CatalogPage', () => {
  it('renders both tabs visible', async () => {
    renderWithProviders(<CatalogPage />)

    expect(await screen.findByText('Your APIs')).toBeInTheDocument()
    expect(screen.getByText('Public Catalog')).toBeInTheDocument()
  })

  it('shows Registered tab empty state by default', async () => {
    renderWithProviders(<CatalogPage />)

    expect(await screen.findByText(/no apis registered yet/i)).toBeInTheDocument()
    expect(screen.getByText(/import apis from the public catalog/i)).toBeInTheDocument()
  })

  it('shows populated API cards on Registered tab', async () => {
    worker.use(
      http.get('/apis', ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('source') === 'local') {
          return HttpResponse.json({
            data: [
              { id: 'stripe-api', name: 'Stripe', source: 'local', description: 'Payment processing' },
              { id: 'github-api', name: 'GitHub', source: 'local', description: 'Code hosting' },
            ],
            total: 2,
            total_pages: 1,
            page: 1,
          })
        }
        return HttpResponse.json({ data: [], total: 0, page: 1 })
      }),
    )

    renderWithProviders(<CatalogPage />)

    expect(await screen.findByText('Stripe')).toBeInTheDocument()
    expect(screen.getByText('GitHub')).toBeInTheDocument()
    expect(screen.getByText('2 APIs registered')).toBeInTheDocument()
  })

  it('shows error state on Registered tab when /apis returns 500', async () => {
    worker.use(createErrorHandler('get', '/apis', { status: 500 }))

    renderWithProviders(<CatalogPage />)

    expect(await screen.findByText(/failed to load registered apis/i)).toBeInTheDocument()
    expect(screen.getByText(/please try refreshing the page/i)).toBeInTheDocument()
  })

  it('shows Catalog tab empty state', async () => {
    worker.use(
      http.get('/catalog', () =>
        HttpResponse.json({ data: [], total: 0, catalog_total: 0, status: 'empty' }),
      ),
    )

    const user = userEvent.setup()
    renderWithProviders(<CatalogPage />)

    await screen.findByText('Your APIs')
    await user.click(screen.getByText('Public Catalog'))

    expect(await screen.findByText(/catalog not synced yet/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sync catalog/i })).toBeInTheDocument()
  })

  it('shows populated catalog entries after switching tab', async () => {
    worker.use(
      http.get('/catalog', () =>
        HttpResponse.json({
          data: [
            { api_id: 'sendgrid-api', description: 'Email delivery', registered: false },
            { api_id: 'twilio-api', description: 'SMS and voice', registered: true },
          ],
          total: 2,
          catalog_total: 100,
          manifest_age_seconds: 3600,
        }),
      ),
    )

    const user = userEvent.setup()
    renderWithProviders(<CatalogPage />)

    await screen.findByText('Your APIs')
    await user.click(screen.getByText('Public Catalog'))

    expect(await screen.findByText('sendgrid-api')).toBeInTheDocument()
    expect(screen.getByText('twilio-api')).toBeInTheDocument()
    expect(screen.getByText(/2 of 100 APIs shown/)).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = renderWithProviders(<CatalogPage />)
    await screen.findByText(/no apis registered yet/i)
    const results = await axe.run(container)
    expect(results.violations).toEqual([])
  })
})
