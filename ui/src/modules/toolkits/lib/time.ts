/**
 * Compact relative-time formatter for toolkit timestamps (created/last-used).
 * Module-local to avoid touching `shared/lib` from a feature PR; promote to
 * `shared` later if a second module needs it.
 */
export function timeAgo(epochMs: number): string {
	if (!Number.isFinite(epochMs)) return '';
	const seconds = Math.round((Date.now() - epochMs) / 1000);
	if (seconds < 60) return 'just now';
	const minutes = Math.round(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.round(hours / 24);
	if (days < 30) return `${days}d ago`;
	const months = Math.round(days / 30);
	if (months < 12) return `${months}mo ago`;
	return `${Math.round(months / 12)}y ago`;
}
