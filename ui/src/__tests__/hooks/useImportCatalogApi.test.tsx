import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { worker } from '../mocks/browser';
import { useImportCatalogApi } from '@/hooks/useImportCatalogApi';

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
	});
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return (
			<QueryClientProvider client={queryClient}>
				<MemoryRouter>{children}</MemoryRouter>
			</QueryClientProvider>
		);
	};
}

describe('useImportCatalogApi', () => {
	it('returns initial state', () => {
		const { result } = renderHook(() => useImportCatalogApi(), { wrapper: createWrapper() });

		expect(result.current.isImporting).toBe(false);
		expect(result.current.error).toBeNull();
		expect(result.current.importedIds.size).toBe(0);
	});

	it('happy path: records imported id and clears error', async () => {
		worker.use(
			http.get('/catalog/my-api', () =>
				HttpResponse.json({ id: 'my-api', spec_url: 'https://example.com/spec.json' }),
			),
			http.post('/import', () => HttpResponse.json({ imported: 1, failed: 0, results: [] })),
		);

		const { result } = renderHook(() => useImportCatalogApi(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.importApi('my-api');
		});

		await waitFor(() => {
			expect(result.current.isImporting).toBe(false);
		});

		expect(result.current.importedIds.has('my-api')).toBe(true);
		expect(result.current.error).toBeNull();
	});

	it('sets error when catalog lookup fails', async () => {
		worker.use(
			http.get('/catalog/bad-api', () =>
				HttpResponse.json({ detail: 'Not found' }, { status: 404 }),
			),
		);

		const { result } = renderHook(() => useImportCatalogApi(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.importApi('bad-api');
		});

		await waitFor(() => {
			expect(result.current.isImporting).toBe(false);
		});

		expect(result.current.error).toMatch(/Not found|Catalog lookup failed/i);
		expect(result.current.importedIds.has('bad-api')).toBe(false);
	});

	it('sets error when catalog entry has no spec_url', async () => {
		worker.use(http.get('/catalog/no-spec', () => HttpResponse.json({ id: 'no-spec' })));

		const { result } = renderHook(() => useImportCatalogApi(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.importApi('no-spec');
		});

		await waitFor(() => {
			expect(result.current.isImporting).toBe(false);
		});

		expect(result.current.error).toMatch(/no spec url/i);
	});

	it('sets error when import endpoint returns failed > 0', async () => {
		worker.use(
			http.get('/catalog/partial-fail', () =>
				HttpResponse.json({
					id: 'partial-fail',
					spec_url: 'https://example.com/spec.json',
				}),
			),
			http.post('/import', () =>
				HttpResponse.json({
					imported: 0,
					failed: 1,
					results: [{ error: 'Spec parse error' }],
				}),
			),
		);

		const { result } = renderHook(() => useImportCatalogApi(), { wrapper: createWrapper() });

		await act(async () => {
			await result.current.importApi('partial-fail');
		});

		await waitFor(() => {
			expect(result.current.isImporting).toBe(false);
		});

		expect(result.current.error).toMatch(/Spec parse error/i);
		expect(result.current.importedIds.has('partial-fail')).toBe(false);
	});
});
