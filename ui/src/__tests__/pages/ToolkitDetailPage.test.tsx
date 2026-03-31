import { screen, waitFor, renderWithProviders, userEvent } from '../test-utils'
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

describe('ToolkitDetailPage — read states', () => {
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

  it('hides Settings button for the default toolkit', async () => {
    worker.use(
      http.get('/toolkits/:id', () =>
        HttpResponse.json({
          id: 'default', name: 'Default Toolkit', description: 'The default',
          disabled: false, credentials: [],
        }),
      ),
    )

    renderToolkit('default')
    await screen.findByText('Default Toolkit')
    expect(screen.queryByRole('button', { name: /settings/i })).not.toBeInTheDocument()
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderToolkit()
    await screen.findByText('Test Toolkit')
    const results = await axe.run(container)
    const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(critical).toEqual([])
  })
})

describe('ToolkitDetailPage — create key flow', () => {
  it('opens key creation form and generates a key', async () => {
    const user = userEvent.setup()

    renderToolkit()
    await screen.findByText('Test Toolkit')

    await user.click(screen.getByRole('button', { name: /create key/i }))
    expect(screen.getByText(/create api key/i)).toBeInTheDocument()

    const input = screen.getByPlaceholderText(/key name/i)
    await user.type(input, 'My Key')
    await user.click(screen.getByRole('button', { name: /generate/i }))

    expect(await screen.findByText(/new api key created/i)).toBeInTheDocument()
  })

  it('shows "Generating..." while key is being created', async () => {
    const user = userEvent.setup()

    worker.use(
      http.post('/toolkits/:id/keys', async () => {
        await delay(500)
        return HttpResponse.json({ id: 'k-new', key: 'jntc_new', prefix: 'jntc_', label: 'Test' })
      }),
    )

    renderToolkit()
    await screen.findByText('Test Toolkit')

    await user.click(screen.getByRole('button', { name: /create key/i }))
    await user.click(screen.getByRole('button', { name: /generate/i }))

    expect(await screen.findByRole('button', { name: /generating/i })).toBeDisabled()
  })
})

describe('ToolkitDetailPage — revoke key flow', () => {
  it('shows revoke confirmation and revokes the key', async () => {
    const user = userEvent.setup()

    worker.use(
      http.get('/toolkits/:id/keys', () =>
        HttpResponse.json({
          keys: [{ id: 'k1', label: 'Old Key', prefix: 'jntc_old', created_at: 1700000000 }],
        }),
      ),
    )

    renderToolkit()
    expect(await screen.findByText('Old Key')).toBeInTheDocument()

    const revokeButton = screen.getByRole('button', { name: /^revoke$/i })
    await user.click(revokeButton)

    expect(screen.getByText(/revoke this key/i)).toBeInTheDocument()

    const confirmButton = screen.getAllByRole('button', { name: /revoke/i }).find(
      btn => btn.textContent?.trim() === 'Revoke'
    )!
    await user.click(confirmButton)

    await waitFor(() => {
      expect(screen.queryByText(/revoke this key/i)).not.toBeInTheDocument()
    })
  })
})

describe('ToolkitDetailPage — kill switch', () => {
  it('shows kill switch confirmation and suspends the toolkit', async () => {
    const user = userEvent.setup()
    let patched = false

    worker.use(
      http.patch('/toolkits/:id', async ({ request }) => {
        const body = await request.json() as Record<string, unknown>
        patched = true
        return HttpResponse.json({
          id: 'test-tk', name: 'Test Toolkit', description: 'A test toolkit',
          disabled: body.disabled, credentials: [],
        })
      }),
    )

    renderToolkit()
    await screen.findByText('Test Toolkit')

    await user.click(screen.getByRole('button', { name: /kill switch/i }))
    expect(screen.getByText(/block all api access/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /kill access/i }))

    await waitFor(() => expect(patched).toBe(true))
  })
})

describe('ToolkitDetailPage — unbind credential', () => {
  it('unbinds a credential via ConfirmInline', async () => {
    const user = userEvent.setup()
    let unbound = false

    worker.use(
      http.get('/toolkits/:id', () =>
        HttpResponse.json({
          id: 'test-tk', name: 'Test Toolkit', description: 'desc',
          disabled: false,
          credentials: [{ credential_id: 'c1', label: 'Stripe Token', api_id: 'stripe.com' }],
        }),
      ),
      http.delete('/toolkits/:id/credentials/:credId', () => {
        unbound = true
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderToolkit()
    expect(await screen.findByText('Stripe Token')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /unbind/i }))
    expect(screen.getByText(/unbind this credential/i)).toBeInTheDocument()

    const confirmBtn = screen.getAllByRole('button', { name: /unbind/i }).find(
      btn => btn.textContent?.trim() === 'Unbind'
    )!
    await user.click(confirmBtn)

    await waitFor(() => expect(unbound).toBe(true))
  })
})
