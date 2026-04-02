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

	it('calls writeText and sets copied to true', async () => {
		const { result } = renderHook(() => useCopyToClipboard());

		await act(async () => {
			await result.current.copy('test-value');
		});

		expect(writeTextSpy).toHaveBeenCalledWith('test-value');
		expect(result.current.copied).toBe(true);
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

	it('keeps copied false when clipboard.writeText rejects', async () => {
		writeTextSpy.mockRejectedValueOnce(new DOMException('Clipboard blocked'));

		const { result } = renderHook(() => useCopyToClipboard());

		await act(async () => {
			await result.current.copy('fail').catch(() => {});
		});

		expect(result.current.copied).toBe(false);
	});
});
