describe('statusVariant', () => {
	let statusVariant: typeof import('@/lib/status').statusVariant;

	beforeAll(async () => {
		({ statusVariant } = await import('@/lib/status'));
	});

	it('returns "default" for null', () => {
		expect(statusVariant(null)).toBe('default');
	});

	it('returns "default" for undefined', () => {
		expect(statusVariant(undefined)).toBe('default');
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

	it('returns "default" for unknown status', () => {
		expect(statusVariant('something_else')).toBe('default');
	});

	it('is case-insensitive', () => {
		expect(statusVariant('SUCCESS')).toBe('success');
		expect(statusVariant('Failed')).toBe('danger');
		expect(statusVariant('WARNING')).toBe('warning');
		expect(statusVariant('Pending')).toBe('pending');
	});
});

describe('statusColor', () => {
	let statusColor: typeof import('@/lib/status').statusColor;

	beforeAll(async () => {
		({ statusColor } = await import('@/lib/status'));
	});

	it('returns "text-muted-foreground" for null', () => {
		expect(statusColor(null)).toBe('text-muted-foreground');
	});

	it('returns "text-muted-foreground" for undefined', () => {
		expect(statusColor(undefined)).toBe('text-muted-foreground');
	});

	it.each([200, 201, 204, 299])('returns "text-success" for 2xx status %i', (code) => {
		expect(statusColor(code)).toBe('text-success');
	});

	it.each([300, 301, 302, 399])('returns "text-accent-yellow" for 3xx status %i', (code) => {
		expect(statusColor(code)).toBe('text-accent-yellow');
	});

	it.each([400, 404, 500, 503])('returns "text-danger" for 4xx/5xx status %i', (code) => {
		expect(statusColor(code)).toBe('text-danger');
	});
});
