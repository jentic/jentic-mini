import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { render, type RenderOptions } from '@testing-library/react'
import type { ReactElement } from 'react'

interface Options extends Omit<RenderOptions, 'wrapper'> {
  route?: string
  path?: string
}

export function renderWithProviders(ui: ReactElement, options: Options = {}) {
  const { route = '/', path, ...renderOptions } = options

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          {path ? (
            <Routes>
              <Route path={path} element={children} />
            </Routes>
          ) : (
            children
          )}
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), queryClient }
}

export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'
