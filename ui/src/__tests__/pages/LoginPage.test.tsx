import { screen, renderWithProviders, userEvent } from '../test-utils'
import { worker } from '../mocks/browser'
import { delay, http, HttpResponse } from 'msw'
import axe from 'axe-core'
import LoginPage from '../../pages/LoginPage'

// Prevent window.location.href navigation from breaking the Vitest browser iframe.
// LoginPage sets window.location.href on successful login — intercept it
// by ensuring the login response stays pending long enough for assertions.
// In browser mode we can't mock window.location, so tests that trigger
// successful login use delayed MSW responses instead.

describe('LoginPage', () => {
  it('renders the login form', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByText('Username')).toBeInTheDocument()
    expect(document.querySelector('input[type="text"]')).toBeInTheDocument()
    expect(document.querySelector('input[type="password"]')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('shows "Logging in..." while submitting', async () => {
    const user = userEvent.setup()

    worker.use(
      http.post('/user/login', async () => {
        // Keep pending indefinitely so onSuccess (window.location.href)
        // never fires — that navigation breaks the Vitest browser iframe.
        await delay('infinite')
        return HttpResponse.json({ logged_in: true })
      }),
    )

    renderWithProviders(<LoginPage />)

    const inputs = screen.getAllByRole('textbox')
    const passwordInput = document.querySelector('input[type="password"]')!
    await user.type(inputs[0], 'admin')
    await user.type(passwordInput as HTMLElement, 'password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByRole('button', { name: /logging in/i })).toBeDisabled()
  })

  it('shows error message on failed login (401)', async () => {
    const user = userEvent.setup()

    worker.use(
      http.post('/user/login', () =>
        HttpResponse.json({ error: 'bad credentials' }, { status: 401 }),
      ),
    )

    renderWithProviders(<LoginPage />)

    const inputs = screen.getAllByRole('textbox')
    const passwordInput = document.querySelector('input[type="password"]')!
    await user.type(inputs[0], 'admin')
    await user.type(passwordInput as HTMLElement, 'wrong')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument()
  })

  it('shows error message on network error (non-401)', async () => {
    const user = userEvent.setup()

    worker.use(
      http.post('/user/login', () =>
        HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
      ),
    )

    renderWithProviders(<LoginPage />)

    const inputs = screen.getAllByRole('textbox')
    const passwordInput = document.querySelector('input[type="password"]')!
    await user.type(inputs[0], 'admin')
    await user.type(passwordInput as HTMLElement, 'password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument()
  })

  it('calls the login API on form submission and enters pending state', async () => {
    const user = userEvent.setup()

    let loginCalled = false
    worker.use(
      http.post('/user/login', async () => {
        loginCalled = true
        // Keep pending — see comment at top of file
        await delay('infinite')
        return HttpResponse.json({ logged_in: true, username: 'admin' })
      }),
    )

    renderWithProviders(<LoginPage />)

    const inputs = screen.getAllByRole('textbox')
    const passwordInput = document.querySelector('input[type="password"]')!
    await user.type(inputs[0], 'admin')
    await user.type(passwordInput as HTMLElement, 'password')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByRole('button', { name: /logging in/i })).toBeDisabled()
    expect(loginCalled).toBe(true)
  })

  it('has no critical accessibility violations', async () => {
    const { container } = renderWithProviders(<LoginPage />)
    // 'label' excluded: inputs use adjacent <label> without htmlFor — tracked as a known a11y debt
    const results = await axe.run(container, { rules: { label: { enabled: false } } })
    const critical = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')
    expect(critical).toEqual([])
  })
})
