import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { worker } from '../mocks/browser';
import { usePendingRequests } from '@/hooks/usePendingRequests';

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false, gcTime: 0 } },
	});
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
	};
}

describe('usePendingRequests', () => {
	it('returns pending requests aggregated across toolkits', async () => {
		worker.use(
			http.get('/toolkits', () =>
				HttpResponse.json([
					{ id: 'tk-1', name: 'Toolkit A' },
					{ id: 'tk-2', name: 'Toolkit B' },
				]),
			),
			http.get('/toolkits/tk-1/access-requests', () =>
				HttpResponse.json([{ id: 'req-1', status: 'pending', reason: 'Need access' }]),
			),
			http.get('/toolkits/tk-2/access-requests', () => HttpResponse.json([])),
		);

		const { result } = renderHook(() => usePendingRequests(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(result.current.data).toBeDefined();
		});

		expect(result.current.data).toHaveLength(1);
		expect(result.current.data![0]).toEqual(
			expect.objectContaining({
				id: 'req-1',
				status: 'pending',
				toolkit_name: 'Toolkit A',
			}),
		);
	});

	it('is disabled when user is not logged in', async () => {
		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'ok' })),
			http.get('/user/me', () => HttpResponse.json({ logged_in: false })),
		);

		const { result } = renderHook(() => usePendingRequests(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(result.current.data).toBeUndefined();
	});
});
