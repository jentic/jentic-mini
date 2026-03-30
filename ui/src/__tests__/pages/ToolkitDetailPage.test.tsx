import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '../test-utils'
import { renderWithProviders } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse, delay } from 'msw'
import axe from 'axe-core'
import ToolkitDetailPage from '../../pages/ToolkitDetailPage'

function renderToolkit(id = 'test-tk') {
  return renderWithProviders(<ToolkitDetailPage />, {
    route: `/toolkits/${id}`,
    path: '/toolkits/:id',
  })
}

describe('ToolkitDetailPage', () => {
  it('renders toolkit name and description', async () => {
    renderToolkit()

    expect(await screen.findByText('Test Toolkit')).toBeInTheDocument()
    expect(screen.getByText('A test toolkit')).toBeInTheDocument()
  })

  it('shows loading state before data arrives', async () => {
    worker.use(
      http.get('/toolkits/:id', async () => {
        await delay(300)
        return HttpResponse.json({
          id: 'test-tk', name: 'Test Toolkit', description: 'A test toolkit',
          disabled: false, credentials: [],
        })
      }),
    )

    renderToolkit()
    expect(screen.getByText(/loading toolkit/i)).toBeInTheDocument()
    expect(await screen.findByText('Test Toolkit')).toBeInTheDocument()
  })

  it('shows "Toolkit not found" when API returns 404', async () => {
    worker.use(
      http.get('/toolkits/:id', () =>
        HttpResponse.json(null, { status: 404 }),
      ),
    )

    renderToolkit()
    expect(await screen.findByText(/toolkit not found/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
  })

  it('shows empty keys message when no keys exist', async () => {
    renderToolkit()

    await screen.findByText('Test Toolkit')
    expect(screen.getByText(/no keys yet/i)).toBeInTheDocument()
  })

  it('renders keys when they exist', async () => {
    worker.use(
      http.get('/toolkits/:id/keys', () =>
        HttpResponse.json({
          keys: [
            { id: 'k1', label: 'Production Key', prefix: 'jntc_abc', created_at: 1700000000 },
          ],
        }),
      ),
    )

    renderToolkit()
    expect(await screen.findByText('Production Key')).toBeInTheDocument()
    expect(screen.getByText('jntc_abc...')).toBeInTheDocument()
  })

  it('renders credentials section', async () => {
    worker.use(
      http.get('/toolkits/:id', () =>
        HttpResponse.json({
          id: 'test-tk', name: 'Test Toolkit', description: 'desc',
          disabled: false,
          credentials: [
            { credential_id: 'c1', label: 'Stripe Token', api_id: 'stripe.com' },
          ],
        }),
      ),
    )

    renderToolkit()
    expect(await screen.findByText('Stripe Token')).toBeInTheDocument()
    expect(screen.getByText('stripe.com')).toBeInTheDocument()
  })

  it('shows pending requests badge', async () => {
    worker.use(
      http.get('/toolkits/:id/access-requests', () =>
        HttpResponse.json([
          { id: 'req1', status: 'pending', type: 'grant', reason: 'Need access' },
        ]),
      ),
    )

    renderToolkit()
    expect(await screen.findByText(/pending access request/i)).toBeInTheDocument()
  })

  it('handles API error gracefully', async () => {
    worker.use(
      http.get('/toolkits/:id', () => HttpResponse.error()),
    )

    renderToolkit()
    expect(await screen.findByText(/toolkit not found/i)).toBeInTheDocument()
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderToolkit()
    await screen.findByText('Test Toolkit')
    const results = await axe.run(container)
    const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(critical).toEqual([])
  })
})
