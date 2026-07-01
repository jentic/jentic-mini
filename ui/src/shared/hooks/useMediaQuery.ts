/**
 * useMediaQuery — subscribe to a CSS media query and re-render when it changes.
 *
 * Used to render genuinely different DOM for small vs. large screens (e.g. a
 * card list on phones vs. a table on desktop) rather than mounting both and
 * toggling with CSS `display` — which would duplicate the content in the
 * accessibility tree and read twice to a screen reader.
 *
 * SPA-only (no SSR), so reading `matchMedia` during the initial state is safe.
 */
import { useEffect, useState } from 'react';

export function useMediaQuery(query: string): boolean {
	const getMatch = () =>
		typeof window !== 'undefined' && typeof window.matchMedia === 'function'
			? window.matchMedia(query).matches
			: false;

	const [matches, setMatches] = useState(getMatch);

	useEffect(() => {
		if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
		const mql = window.matchMedia(query);
		const onChange = () => setMatches(mql.matches);
		// Sync once in case the query changed between render and effect.
		onChange();
		mql.addEventListener('change', onChange);
		return () => mql.removeEventListener('change', onChange);
	}, [query]);

	return matches;
}
