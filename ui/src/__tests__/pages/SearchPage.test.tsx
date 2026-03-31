import { screen, waitFor, renderWithProviders } from '../test-utils'
import { worker } from '../mocks/browser'
import { http, HttpResponse } from 'msw'
import axe from 'axe-core'
import SearchPage from '../../pages/SearchPage'

describe('SearchPage', () => {
  it('renders heading and search input', async () => {
    renderWithProviders(<SearchPage />)
    expect(await screen.findByRole('heading', { name: /search/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/search apis/i)).toBeInTheDocument()
  })

  it('shows example queries in initial state', async () => {
    renderWithProviders(<SearchPage />)
    await screen.findByRole('heading', { name: /search/i })
    expect(screen.getByText('send an email')).toBeInTheDocument()
    expect(screen.getByText('post a Slack message')).toBeInTheDocument()
  })

  it('shows results when search query matches', async () => {
    worker.use(
      http.get('/search', ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('q')) {
          return HttpResponse.json([
            { id: 'POST/api.sendgrid.com/v3/mail/send', type: 'operation', source: 'local', summary: 'Send an email', score: 0.95 },
            { id: 'POST/api.mailgun.com/v3/messages', type: 'operation', source: 'catalog', summary: 'Send message', score: 0.8 },
          ])
        }
        return HttpResponse.json([])
      }),
    )

    renderWithProviders(<SearchPage />, { route: '/search?q=send+email' })

    expect(await screen.findByText('Send an email')).toBeInTheDocument()
    expect(screen.getByText('Send message')).toBeInTheDocument()
    expect(screen.getByText(/2 results/)).toBeInTheDocument()
  })

  it('shows empty state for queries with no results', async () => {
    worker.use(
      http.get('/search', () => HttpResponse.json([])),
    )

    renderWithProviders(<SearchPage />, { route: '/search?q=xyznonexistent' })

    expect(await screen.findByText(/no results for/i)).toBeInTheDocument()
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderWithProviders(<SearchPage />)
    await screen.findByRole('heading', { name: /search/i })
    const results = await axe.run(container)
    const serious = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(serious).toEqual([])
  })
})
