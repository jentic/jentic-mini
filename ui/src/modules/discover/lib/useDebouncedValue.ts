/**
 * useDebouncedValue — returns `value` after it has stopped changing for `delay`
 * ms. Used by the Discover search box so we don't fire a query on every
 * keystroke. Kept module-local (not in @/shared) since it's the only consumer
 * for now; promote to shared if a second module needs it.
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
