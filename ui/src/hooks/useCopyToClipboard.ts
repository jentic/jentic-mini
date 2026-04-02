import { useState, useCallback, useRef } from 'react';

export function useCopyToClipboard(resetMs = 2000) {
	const [copied, setCopied] = useState(false);
	const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const copy = useCallback(
		async (value: string) => {
			await navigator.clipboard.writeText(value);
			setCopied(true);
			if (timeoutRef.current) clearTimeout(timeoutRef.current);
			timeoutRef.current = setTimeout(() => setCopied(false), resetMs);
		},
		[resetMs],
	);

	return { copied, copy };
}
