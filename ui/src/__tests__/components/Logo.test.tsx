import { render, screen } from '@testing-library/react';
import { JenticLogo } from '@/components/ui/Logo';

describe('JenticLogo', () => {
	it('renders the SVG and "Mini" badge', () => {
		render(<JenticLogo />);
		expect(screen.getByText('Mini')).toBeInTheDocument();
		const svg = document.querySelector('svg');
		expect(svg).toBeInTheDocument();
	});

	it('applies custom className to the SVG', () => {
		render(<JenticLogo className="h-20" />);
		const svg = document.querySelector('svg')!;
		expect(svg.className.baseVal).toContain('h-20');
	});

	it('SVG has aria-hidden for decorative usage', () => {
		render(<JenticLogo />);
		const svg = document.querySelector('svg')!;
		expect(svg.getAttribute('aria-hidden')).toBe('true');
	});

	it('defaults to h-10 className', () => {
		render(<JenticLogo />);
		const svg = document.querySelector('svg')!;
		expect(svg.className.baseVal).toContain('h-10');
	});
});
