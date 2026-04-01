import { renderHook, act } from '@testing-library/react';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';

let writeTextSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
	vi.useFakeTimers();
	writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
});

afterEach(() => {
	vi.useRealTimers();
	writeTextSpy.mockRestore();
});

describe('useCopyToClipboard', () => {
	it('initially has copied = false', () => {
		const { result } = renderHook(() => useCopyToClipboard());
		expect(result.current.copied).toBe(false);
	});

	it('sets copied to true after calling copy', async () => {
		const { result } = renderHook(() => useCopyToClipboard());

		await act(async () => {
			await result.current.copy('hello');
		});

		expect(result.current.copied).toBe(true);
	});

	it('calls navigator.clipboard.writeText with the provided value', async () => {
		const { result } = renderHook(() => useCopyToClipboard());

		await act(async () => {
			await result.current.copy('test-value');
		});

		expect(writeTextSpy).toHaveBeenCalledWith('test-value');
	});

	it('resets copied to false after the timeout', async () => {
		const { result } = renderHook(() => useCopyToClipboard(1000));

		await act(async () => {
			await result.current.copy('hello');
		});

		expect(result.current.copied).toBe(true);

		await act(async () => {
			vi.advanceTimersByTime(1000);
		});

		expect(result.current.copied).toBe(false);
	});

	it('uses default 2000ms reset timeout', async () => {
		const { result } = renderHook(() => useCopyToClipboard());

		await act(async () => {
			await result.current.copy('hello');
		});

		await act(async () => {
			vi.advanceTimersByTime(1999);
		});
		expect(result.current.copied).toBe(true);

		await act(async () => {
			vi.advanceTimersByTime(1);
		});
		expect(result.current.copied).toBe(false);
	});
});
