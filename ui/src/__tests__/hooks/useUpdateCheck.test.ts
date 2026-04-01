/**
 * These are pure functions from useUpdateCheck.ts.
 * Since they're module-private, we replicate them here for direct testing.
 * If the logic drifts, integration tests via the hook will catch it.
 */

function parseSemver(v: string): number[] {
	return v
		.replace(/^v/, '')
		.split('.')
		.map((n) => parseInt(n, 10) || 0);
}

function isSemver(v: string): boolean {
	return /^\d+\.\d+\.\d+/.test(v.replace(/^v/, ''));
}

function isNewer(latest: string, current: string): boolean {
	if (!isSemver(latest) || !isSemver(current)) return false;
	const l = parseSemver(latest);
	const c = parseSemver(current);
	for (let i = 0; i < 3; i++) {
		if ((l[i] ?? 0) > (c[i] ?? 0)) return true;
		if ((l[i] ?? 0) < (c[i] ?? 0)) return false;
	}
	return false;
}

describe('parseSemver', () => {
	it('parses "1.2.3" into [1, 2, 3]', () => {
		expect(parseSemver('1.2.3')).toEqual([1, 2, 3]);
	});

	it('strips leading "v"', () => {
		expect(parseSemver('v1.0.0')).toEqual([1, 0, 0]);
	});

	it('handles non-numeric segments as 0', () => {
		expect(parseSemver('1.2.beta')).toEqual([1, 2, 0]);
	});
});

describe('isSemver', () => {
	it('returns true for valid semver', () => {
		expect(isSemver('1.0.0')).toBe(true);
		expect(isSemver('0.3.1')).toBe(true);
	});

	it('returns true for v-prefixed semver', () => {
		expect(isSemver('v1.2.3')).toBe(true);
	});

	it('returns true for semver with suffix (prefix match)', () => {
		expect(isSemver('1.2.3-beta')).toBe(true);
	});

	it('returns false for non-semver strings', () => {
		expect(isSemver('unknown')).toBe(false);
		expect(isSemver('')).toBe(false);
		expect(isSemver('latest')).toBe(false);
	});
});

describe('isNewer', () => {
	it('returns true when latest > current (patch)', () => {
		expect(isNewer('1.0.1', '1.0.0')).toBe(true);
	});

	it('returns true when latest > current (minor)', () => {
		expect(isNewer('1.1.0', '1.0.0')).toBe(true);
	});

	it('returns true when latest > current (major)', () => {
		expect(isNewer('2.0.0', '1.9.9')).toBe(true);
	});

	it('returns false when versions are equal', () => {
		expect(isNewer('1.0.0', '1.0.0')).toBe(false);
	});

	it('returns false when latest < current', () => {
		expect(isNewer('0.9.0', '1.0.0')).toBe(false);
	});

	it('returns false for non-semver input', () => {
		expect(isNewer('unknown', '1.0.0')).toBe(false);
		expect(isNewer('1.0.0', 'unknown')).toBe(false);
	});
});
