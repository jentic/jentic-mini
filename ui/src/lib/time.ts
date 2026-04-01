export function timeAgo(ts: number | null | undefined): string {
	if (!ts) return '';
	const secs = Math.floor(Date.now() / 1000 - ts);
	if (secs < 0) return 'just now';
	if (secs < 60) return `${secs}s ago`;
	if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
	if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
	return `${Math.floor(secs / 86400)}d ago`;
}

export function formatTimestamp(ts: number | null | undefined): string {
	if (!ts) return '';
	return new Date(ts * 1000).toLocaleString();
}
