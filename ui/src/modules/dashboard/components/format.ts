/**
 * Dashboard view helpers — small, pure formatting utilities used by the
 * overview components. Relative-time formatting lives in the shared
 * `@/shared/lib/utils` `timeAgo` (promoted by ui-agents under COLLABORATION §4);
 * this file keeps only the dashboard-specific bits.
 */

/** Render a 0..1 ratio as a whole-percent string, or "—" when null. */
export function formatPercent(ratio: number | null): string {
	if (ratio == null) return '—';
	return `${Math.round(ratio * 100)}%`;
}
