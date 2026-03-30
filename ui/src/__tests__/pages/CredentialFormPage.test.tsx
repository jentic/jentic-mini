import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '../test-utils'
import { renderWithProviders } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import CredentialFormPage from '../../pages/CredentialFormPage'

describe('CredentialFormPage — create mode', () => {
  it('renders the heading and API picker', async () => {
    renderWithProviders(<CredentialFormPage />)

    expect(await screen.findByRole('heading', { name: /add credential/i })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/search apis/i)).toBeInTheDocument()
  })

  it('shows the empty state prompt', async () => {
    renderWithProviders(<CredentialFormPage />)

    expect(await screen.findByText(/start typing to search/i)).toBeInTheDocument()
  })

  it('shows search results when user types', async () => {
    const { userEvent } = await import('../test-utils')
    const user = userEvent.setup()

    worker.use(
      http.get('/apis', ({ request }) => {
        const url = new URL(request.url)
        const q = url.searchParams.get('q')
        if (q?.includes('stripe')) {
          return HttpResponse.json({
            data: [{ id: 'stripe', name: 'Stripe', description: 'Payment processing', source: 'local' }],
            total: 1,
            page: 1,
          })
        }
        return HttpResponse.json({ data: [], total: 0, page: 1 })
      }),
    )

    renderWithProviders(<CredentialFormPage />)

    const input = await screen.findByPlaceholderText(/search apis/i)
    await user.type(input, 'stripe')

    expect(await screen.findByText('Stripe')).toBeInTheDocument()
  })

  it('shows "no APIs found" for empty search results', async () => {
    const { userEvent } = await import('../test-utils')
    const user = userEvent.setup()

    worker.use(
      http.get('/apis', () =>
        HttpResponse.json({ data: [], total: 0, page: 1 }),
      ),
    )

    renderWithProviders(<CredentialFormPage />)

    const input = await screen.findByPlaceholderText(/search apis/i)
    await user.type(input, 'nonexistent')

    expect(await screen.findByText(/no apis found/i)).toBeInTheDocument()
  })

  it('has no accessibility violations', async () => {
    const { container } = renderWithProviders(<CredentialFormPage />)
    await screen.findByRole('heading', { name: /add credential/i })
    const results = await axe.run(container)
    expect(results.violations).toEqual([])
  })
})

describe('CredentialFormPage — edit mode', () => {
  it('renders "Edit Credential" heading in edit mode', async () => {
    worker.use(
      http.get('/credentials/:id', () =>
        HttpResponse.json({
          id: 'cred-1', label: 'My Token', api_id: 'stripe', auth_type: 'bearer',
        }),
      ),
      http.get('/apis/stripe', () =>
        HttpResponse.json({
          id: 'stripe', name: 'Stripe', source: 'local',
          security_schemes: { bearerAuth: { type: 'http', scheme: 'bearer' } },
        }),
      ),
    )

    renderWithProviders(<CredentialFormPage />, {
      route: '/credentials/cred-1/edit',
      path: '/credentials/:id/edit',
    })

    expect(await screen.findByRole('heading', { name: /edit credential/i })).toBeInTheDocument()
  })
})
