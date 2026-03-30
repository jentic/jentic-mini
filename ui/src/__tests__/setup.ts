import '@testing-library/jest-dom/vitest'
import { worker } from './mocks/browser'

beforeAll(async () => {
  await worker.start({ onUnhandledRequest: 'warn' })
})

afterEach(() => {
  worker.resetHandlers()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

afterAll(() => {
  worker.stop()
})
