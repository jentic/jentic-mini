import { screen, renderWithProviders } from '../test-utils'
import { worker } from '../mocks/browser'
import { delay, http, HttpResponse } from 'msw'
import { AuthGuard } from '../../components/AuthGuard'
import { Routes, Route } from 'react-router-dom'

function renderWithAuth(initialRoute: string) {
  return renderWithProviders(
    <Routes>
      <Route element={<AuthGuard />}>
        <Route path="/setup" element={<div>Setup Page</div>} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/" element={<div>Dashboard</div>} />
        <Route path="/toolkits" element={<div>Toolkits</div>} />
      </Route>
    </Routes>,
    { route: initialRoute, path: undefined },
  )
}

describe('AuthGuard', () => {
  it('shows loading state while checking auth', () => {
    worker.use(
      http.get('/health', async () => {
        await delay('infinite')
        return HttpResponse.json({ status: 'ok' })
      }),
    )

    renderWithAuth('/')
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('redirects to /setup when setup is required', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'setup_required' }),
      ),
    )

    renderWithAuth('/toolkits')
    expect(await screen.findByText('Setup Page')).toBeInTheDocument()
  })

  it('renders setup page when already on /setup', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'setup_required' }),
      ),
    )

    renderWithAuth('/setup')
    expect(await screen.findByText('Setup Page')).toBeInTheDocument()
  })

  it('redirects to /login when not authenticated', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'ok' }),
      ),
      http.get('/user/me', () =>
        HttpResponse.json({ logged_in: false }),
      ),
    )

    renderWithAuth('/toolkits')
    expect(await screen.findByText('Login Page')).toBeInTheDocument()
  })

  it('renders protected page when authenticated', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'ok' }),
      ),
      http.get('/user/me', () =>
        HttpResponse.json({ logged_in: true, username: 'admin' }),
      ),
    )

    renderWithAuth('/toolkits')
    expect(await screen.findByText('Toolkits')).toBeInTheDocument()
  })

  it('redirects authenticated user away from /login to /', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'ok' }),
      ),
      http.get('/user/me', () =>
        HttpResponse.json({ logged_in: true, username: 'admin' }),
      ),
    )

    renderWithAuth('/login')
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('redirects authenticated user away from /setup to /', async () => {
    worker.use(
      http.get('/health', () =>
        HttpResponse.json({ status: 'ok' }),
      ),
      http.get('/user/me', () =>
        HttpResponse.json({ logged_in: true, username: 'admin' }),
      ),
    )

    renderWithAuth('/setup')
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })
})
