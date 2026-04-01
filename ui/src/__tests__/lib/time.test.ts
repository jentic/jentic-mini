describe('timeAgo', () => {
	let timeAgo: typeof import('@/lib/time').timeAgo;

	beforeAll(async () => {
		({ timeAgo } = await import('@/lib/time'));
	});

	it('returns empty string for null', () => {
		expect(timeAgo(null)).toBe('');
	});

	it('returns empty string for undefined', () => {
		expect(timeAgo(undefined)).toBe('');
	});

	it('returns empty string for 0', () => {
		expect(timeAgo(0)).toBe('');
	});

	it('returns "just now" for future timestamps', () => {
		const future = Math.floor(Date.now() / 1000) + 600;
		expect(timeAgo(future)).toBe('just now');
	});

	it('returns seconds format for < 60s', () => {
		const ts = Math.floor(Date.now() / 1000) - 30;
		expect(timeAgo(ts)).toBe('30s ago');
	});

	it('returns minutes format for < 1h', () => {
		const ts = Math.floor(Date.now() / 1000) - 300;
		expect(timeAgo(ts)).toBe('5m ago');
	});

	it('returns hours format for < 24h', () => {
		const ts = Math.floor(Date.now() / 1000) - 7200;
		expect(timeAgo(ts)).toBe('2h ago');
	});

	it('returns days format for >= 24h', () => {
		const ts = Math.floor(Date.now() / 1000) - 172800;
		expect(timeAgo(ts)).toBe('2d ago');
	});
});

describe('formatTimestamp', () => {
	let formatTimestamp: typeof import('@/lib/time').formatTimestamp;

	beforeAll(async () => {
		({ formatTimestamp } = await import('@/lib/time'));
	});

	it('returns empty string for null', () => {
		expect(formatTimestamp(null)).toBe('');
	});

	it('returns empty string for undefined', () => {
		expect(formatTimestamp(undefined)).toBe('');
	});

	it('returns empty string for 0', () => {
		expect(formatTimestamp(0)).toBe('');
	});

	it('returns a formatted date string for a valid timestamp', () => {
		const ts = 1700000000;
		const result = formatTimestamp(ts);
		expect(result).toBe(new Date(ts * 1000).toLocaleString());
	});
});
