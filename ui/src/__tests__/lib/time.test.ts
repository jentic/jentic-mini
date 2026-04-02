describe('timeAgo', () => {
	let timeAgo: typeof import('@/lib/time').timeAgo;

	beforeAll(async () => {
		({ timeAgo } = await import('@/lib/time'));
	});

	it('returns empty string for falsy values', () => {
		expect(timeAgo(null)).toBe('');
		expect(timeAgo(undefined)).toBe('');
		expect(timeAgo(0)).toBe('');
	});

	it('returns "just now" for future timestamps', () => {
		expect(timeAgo(Math.floor(Date.now() / 1000) + 600)).toBe('just now');
	});

	it.each([
		[30, '30s ago'],
		[300, '5m ago'],
		[7200, '2h ago'],
		[172800, '2d ago'],
	])('formats %i seconds ago as "%s"', (secsAgo, expected) => {
		const ts = Math.floor(Date.now() / 1000) - secsAgo;
		expect(timeAgo(ts)).toBe(expected);
	});
});

describe('formatTimestamp', () => {
	let formatTimestamp: typeof import('@/lib/time').formatTimestamp;

	beforeAll(async () => {
		({ formatTimestamp } = await import('@/lib/time'));
	});

	it('returns empty string for falsy values', () => {
		expect(formatTimestamp(null)).toBe('');
		expect(formatTimestamp(undefined)).toBe('');
		expect(formatTimestamp(0)).toBe('');
	});

	it('returns locale string for valid timestamp', () => {
		const ts = 1700000000;
		expect(formatTimestamp(ts)).toBe(new Date(ts * 1000).toLocaleString());
	});
});
