import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { worker } from '../mocks/browser';
import { useUpdateCheck } from '@/hooks/useUpdateCheck';

beforeEach(() => {
	sessionStorage.removeItem('jentic_update_check');
});

describe('useUpdateCheck', () => {
	it('returns update info when a newer version exists', async () => {
		worker.use(
			http.get('/version', () =>
				HttpResponse.json({
					current: '0.2.0',
					latest: '0.3.0',
					release_url: 'https://github.com/release/0.3.0',
				}),
			),
		);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.updateAvailable).toBe(true);
		});

		expect(result.current.currentVersion).toBe('0.2.0');
		expect(result.current.latestVersion).toBe('0.3.0');
		expect(result.current.releaseUrl).toBe('https://github.com/release/0.3.0');
	});

	it('returns no update when versions match', async () => {
		worker.use(
			http.get('/version', () => HttpResponse.json({ current: '1.0.0', latest: '1.0.0' })),
		);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.currentVersion).toBe('1.0.0');
		});

		expect(result.current.updateAvailable).toBe(false);
	});

	it('returns no update when latest is older', async () => {
		worker.use(
			http.get('/version', () => HttpResponse.json({ current: '2.0.0', latest: '1.9.0' })),
		);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.currentVersion).toBe('2.0.0');
		});

		expect(result.current.updateAvailable).toBe(false);
	});

	it('uses sessionStorage cache on subsequent renders', async () => {
		const cached = JSON.stringify({
			currentVersion: '0.1.0',
			latestVersion: '0.2.0',
			updateAvailable: true,
			releaseUrl: 'https://cached',
		});
		sessionStorage.setItem('jentic_update_check', cached);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.updateAvailable).toBe(true);
		});

		expect(result.current.currentVersion).toBe('0.1.0');
		expect(result.current.releaseUrl).toBe('https://cached');
	});

	it('handles network errors silently', async () => {
		worker.use(http.get('/version', () => HttpResponse.error()));

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.currentVersion).toBeNull();
		});

		expect(result.current.updateAvailable).toBe(false);
	});

	it('sets currentVersion even when latest is null (telemetry off)', async () => {
		worker.use(
			http.get('/version', () =>
				HttpResponse.json({ current: '0.5.3', latest: null, release_url: null }),
			),
		);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.currentVersion).toBe('0.5.3');
		});

		expect(result.current.updateAvailable).toBe(false);
		expect(result.current.latestVersion).toBeNull();
		expect(result.current.releaseUrl).toBeNull();
	});

	it('handles non-semver current version', async () => {
		worker.use(
			http.get('/version', () => HttpResponse.json({ current: 'unknown', latest: '1.0.0' })),
		);

		const { result } = renderHook(() => useUpdateCheck());

		await waitFor(() => {
			expect(result.current.currentVersion).toBe('unknown');
		});

		expect(result.current.updateAvailable).toBe(false);
	});
});
