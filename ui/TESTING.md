# Testing Guide

How to write and run tests for the Jentic Mini UI.

## Running Tests

```bash
# Unit + integration tests (Vitest browser mode)
npm test

# Single run (CI)
npm run test:run

# With coverage report
npm run test:coverage

# E2E tests (Playwright)
npm run test:e2e

# E2E with interactive UI
npm run test:e2e:ui

# Docker E2E (real backend)
npm run test:e2e:docker  # requires Docker running
```

## Test Layers

| Layer        | Tool                     | What to test                           |
| ------------ | ------------------------ | -------------------------------------- |
| Static       | TypeScript + ESLint      | Types, imports, syntax                 |
| Unit         | Vitest + Testing Library | Pure logic, UI primitives              |
| Integration  | Vitest + MSW             | Full pages with network mocking        |
| E2E (mocked) | Playwright               | Critical user journeys with mocked API |
| E2E (Docker) | Playwright               | Critical paths against real backend    |

**Integration tests are the core.** They render real components with real React Query, real Router, and real DOM — mocking only the network layer via MSW.

## File Structure

```
src/__tests__/
  setup.ts                    # Global setup (jest-dom, MSW worker lifecycle, storage cleanup)
  test-utils.tsx              # renderWithProviders + createErrorHandler helpers
  mocks/
    handlers.ts               # Shared MSW handlers (happy path — reads + mutations)
    browser.ts                # MSW browser worker instance
  components/                 # Unit tests for UI primitives + AuthGuard
  hooks/                      # Unit tests for pure logic hooks
  pages/                      # Integration tests for all pages

e2e/                          # Playwright mocked E2E tests
e2e/docker/                   # Playwright Docker E2E tests (real backend)
```

## Writing a New Integration Test

1. Import `renderWithProviders`, `screen`, and `userEvent` from `../test-utils`
2. Import `worker` from `../mocks/browser` for handler overrides
3. Wrap assertions in `await screen.findBy*` (data loads async via React Query)
4. Test four states: **loading**, **empty**, **populated**, **error**

```tsx
import { screen, renderWithProviders, userEvent } from '../test-utils';
import { worker } from '../mocks/browser';
import { http, HttpResponse } from 'msw';
import MyPage from '../../pages/MyPage';

describe('MyPage', () => {
	it('renders with populated data', async () => {
		worker.use(http.get('/my-endpoint', () => HttpResponse.json([{ id: '1', name: 'Item' }])));
		renderWithProviders(<MyPage />);
		expect(await screen.findByText('Item')).toBeInTheDocument();
	});

	it('handles error gracefully', async () => {
		worker.use(http.get('/my-endpoint', () => HttpResponse.error()));
		renderWithProviders(<MyPage />);
		expect(await screen.findByRole('heading')).toBeInTheDocument();
	});

	it('completes a mutation round-trip', async () => {
		const user = userEvent.setup();
		let mutationCalled = false;

		worker.use(
			http.post('/my-endpoint', () => {
				mutationCalled = true;
				return HttpResponse.json({ id: 'new', name: 'Created' });
			}),
		);

		renderWithProviders(<MyPage />);
		await user.click(screen.getByRole('button', { name: /create/i }));
		// Verify the mutation was called and UI updated
	});
});
```

## Adding MSW Handlers

Add new handlers to `src/__tests__/mocks/handlers.ts` for the happy path. The handler set includes both read (GET) and mutation (POST/PATCH/DELETE) endpoints. Use `worker.use()` in individual tests for error/edge cases.

All API calls use relative paths (e.g., `/toolkits`, `/apis`). MSW intercepts these directly.

## Using `renderWithProviders` with Route Params

For pages that use `useParams()`:

```tsx
renderWithProviders(<ToolkitDetailPage />, {
	route: '/toolkits/tk-1',
	path: '/toolkits/:id',
});
```

## Test Isolation

Each test gets:

- A fresh `QueryClient` with `retry: false` and `gcTime: 0` (no cache leakage)
- MSW handlers reset to defaults via `worker.resetHandlers()`
- `localStorage` and `sessionStorage` cleared

## Rules of Thumb

1. **Mock the network, never the hooks.** Let `useQuery`/`useMutation` run for real. Mock at the `fetch()` layer via MSW.
2. **Don't mock child components.** Render the full component tree. Integration means integration.
3. **Test behavior, not implementation.** Query by role/text/label, not by CSS class or DOM structure.
4. **Each test should test one user-visible outcome.** Not "renders correctly" — instead "shows toolkit name from API response".
5. **Use `screen.findBy*` (async) for data that loads via React Query.** Data arrives asynchronously — `findBy` waits; `getBy` doesn't.
6. **Override MSW handlers per-test for edge cases.** The shared handlers define the happy path. Use `worker.use()` inside individual tests.
7. **Keep E2E tests thin.** Playwright tests verify page-level smoke. Detailed interaction testing belongs in Vitest where it runs 10x faster.
8. **One a11y check per critical page.** Use `axe-core` in integration tests to catch common violations.
9. **Never snapshot.** Snapshot tests create false confidence and break on any render change.
