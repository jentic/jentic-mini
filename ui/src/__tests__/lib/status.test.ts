describe('statusVariant', () => {
	let statusVariant: typeof import('@/lib/status').statusVariant;

	beforeAll(async () => {
		({ statusVariant } = await import('@/lib/status'));
	});

	it('returns "default" for null/undefined/unknown', () => {
		expect(statusVariant(null)).toBe('default');
		expect(statusVariant(undefined)).toBe('default');
		expect(statusVariant('something_else')).toBe('default');
	});

	it.each(['success', 'completed', 'ok', 'active'])('returns "success" for "%s"', (status) => {
		expect(statusVariant(status)).toBe('success');
	});

	it.each(['failed', 'error', 'rejected', 'denied'])('returns "danger" for "%s"', (status) => {
		expect(statusVariant(status)).toBe('danger');
	});

	it.each(['warning', 'timeout'])('returns "warning" for "%s"', (status) => {
		expect(statusVariant(status)).toBe('warning');
	});

	it.each(['pending', 'running', 'in_progress'])('returns "pending" for "%s"', (status) => {
		expect(statusVariant(status)).toBe('pending');
	});

	it('is case-insensitive', () => {
		expect(statusVariant('SUCCESS')).toBe('success');
		expect(statusVariant('Failed')).toBe('danger');
	});
});

describe('statusColor', () => {
	let statusColor: typeof import('@/lib/status').statusColor;

	beforeAll(async () => {
		({ statusColor } = await import('@/lib/status'));
	});

	it('returns "text-muted-foreground" for null/undefined', () => {
		expect(statusColor(null)).toBe('text-muted-foreground');
		expect(statusColor(undefined)).toBe('text-muted-foreground');
	});

	it.each([200, 201, 299])('returns "text-success" for %i', (code) => {
		expect(statusColor(code)).toBe('text-success');
	});

	it.each([300, 301, 399])('returns "text-accent-yellow" for %i', (code) => {
		expect(statusColor(code)).toBe('text-accent-yellow');
	});

	it.each([400, 404, 500, 503])('returns "text-danger" for %i', (code) => {
		expect(statusColor(code)).toBe('text-danger');
	});
});
