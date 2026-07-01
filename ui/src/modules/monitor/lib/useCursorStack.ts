/**
 * Cursor pagination stack for Monitor list tabs.
 *
 * The Monitor list endpoints are forward-only cursor APIs: each page returns
 * `has_more` + `next_cursor`, but there's no "previous cursor". To support a
 * "Newer / Older" pager we keep a stack of the cursors we've stepped through:
 *
 *   - start: stack = []          -> current cursor = null (first page)
 *   - Older: push `next_cursor`  -> current cursor = that cursor
 *   - Newer: pop                 -> current cursor = the previous frame
 *
 * `reset()` clears the stack (call it whenever a filter changes so paging
 * restarts from page 1). `filterKey` does this automatically: pass a string
 * that encodes the active filters and the stack resets when it changes.
 */
import { useRef, useState } from 'react';

export interface CursorStack {
	/** Cursor to send for the current page (null = first page). */
	cursor: string | null;
	/** True when not on the first page (so "Newer" is enabled). */
	hasPrev: boolean;
	/** 1-based index of the current page (for the pager indicator). */
	page: number;
	/** Advance to the next page using the response's `next_cursor`. */
	pushNext: (nextCursor: string | null | undefined) => void;
	/** Step back to the previous page. */
	goPrev: () => void;
	/** Restart paging from the first page. */
	reset: () => void;
}

export function useCursorStack(filterKey: string): CursorStack {
	const [stack, setStack] = useState<string[]>([]);
	const prevKey = useRef(filterKey);

	// Reset to page 1 whenever the filters change. We adjust state DURING render
	// (not in an effect) so the same render that sees the new filterKey also
	// pages from the start — otherwise the query fires once with the stale cursor
	// from the previous filter's result set (wrong page + an extra request).
	// `setStack` during render makes React re-run this component immediately with
	// the empty stack before committing, so we also treat the in-flight render as
	// already-empty via `effectiveStack`.
	let effectiveStack = stack;
	if (prevKey.current !== filterKey) {
		prevKey.current = filterKey;
		effectiveStack = [];
		setStack([]);
	}

	const cursor = effectiveStack.length > 0 ? effectiveStack[effectiveStack.length - 1] : null;

	const pushNext = (nextCursor: string | null | undefined) => {
		if (!nextCursor) return;
		setStack((prev) => [...prev, nextCursor]);
	};

	const goPrev = () => setStack((prev) => prev.slice(0, -1));

	const reset = () => setStack([]);

	return {
		cursor,
		hasPrev: effectiveStack.length > 0,
		page: effectiveStack.length + 1,
		pushNext,
		goPrev,
		reset,
	};
}
