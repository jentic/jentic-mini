describe('cn', () => {
	let cn: typeof import('@/lib/utils').cn;

	beforeAll(async () => {
		({ cn } = await import('@/lib/utils'));
	});

	it('merges class names', () => {
		expect(cn('px-2', 'py-1')).toBe('px-2 py-1');
	});

	it('handles conditional classes', () => {
		const isHidden = false;
		expect(cn('base', isHidden && 'hidden', 'visible')).toBe('base visible');
	});

	it('deduplicates conflicting Tailwind classes', () => {
		expect(cn('px-2', 'px-4')).toBe('px-4');
	});

	it('handles undefined and null inputs', () => {
		expect(cn('base', undefined, null, 'extra')).toBe('base extra');
	});
});
