/**
 * useDebouncedValue — returns `value` after it has stopped changing for `delay`
 * ms. Used by search/filter boxes so we don't fire a query on every keystroke.
 *
 * Promoted to `@/shared/hooks` once a second module (credentials) needed the
 * same behaviour the Discover search box introduced.
 */
import { useEffect, useState } from 'react';

export function useDebouncedValue<T>(value: T, delay: number): T {
	const [debounced, setDebounced] = useState(value);

	useEffect(() => {
		const handle = setTimeout(() => setDebounced(value), delay);
		return () => clearTimeout(handle);
	}, [value, delay]);

	return debounced;
}
