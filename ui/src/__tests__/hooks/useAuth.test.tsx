import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { worker } from '../mocks/browser';
import { useAuth } from '@/hooks/useAuth';

function createWrapper() {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false, gcTime: 0 } },
	});
	return function Wrapper({ children }: { children: React.ReactNode }) {
		return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
	};
}

describe('useAuth', () => {
	it('returns user when setup is complete and session is valid', async () => {
		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(result.current.user).toEqual(
			expect.objectContaining({ logged_in: true, username: 'admin' }),
		);
		expect(result.current.isSetupOrAccountRequired).toBe(false);
	});

	it('returns isSetupOrAccountRequired when health says setup_required', async () => {
		worker.use(http.get('/health', () => HttpResponse.json({ status: 'setup_required' })));

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(result.current.isSetupOrAccountRequired).toBe(true);
		expect(result.current.user).toBeUndefined();
	});

	it('does not fetch user when setup is not complete', async () => {
		worker.use(
			http.get('/health', () => HttpResponse.json({ status: 'setup_required' })),
			http.get('/user/me', () => {
				throw new Error('Should not be called');
			}),
		);

		const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

		await waitFor(() => {
			expect(result.current.isLoading).toBe(false);
		});

		expect(result.current.isSetupOrAccountRequired).toBe(true);
	});
});
