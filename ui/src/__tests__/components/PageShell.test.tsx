import { render } from '@testing-library/react';
import { PageShell } from '@/components/layout/PageShell';

function getShell(container: HTMLElement) {
	return container.firstElementChild as HTMLElement;
}

describe('PageShell', () => {
	it('renders children inside a centred container', () => {
		const { container, getByText } = render(
			<PageShell>
				<p>hello</p>
			</PageShell>,
		);
		expect(getByText('hello')).toBeInTheDocument();
		const shell = getShell(container);
		expect(shell.className).toContain('mx-auto');
		expect(shell.className).toContain('w-full');
	});

	it('defaults to the wide variant (max-w-screen-2xl)', () => {
		const { container } = render(
			<PageShell>
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('max-w-screen-2xl');
	});

	it('uses max-w-4xl for the reading variant', () => {
		const { container } = render(
			<PageShell width="reading">
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('max-w-4xl');
		expect(getShell(container).className).not.toContain('max-w-screen-2xl');
	});

	it('uses max-w-2xl for the form variant', () => {
		const { container } = render(
			<PageShell width="form">
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('max-w-2xl');
	});

	it('applies the default space-y-6 vertical rhythm', () => {
		const { container } = render(
			<PageShell>
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('space-y-6');
	});

	it('accepts a custom spacing class', () => {
		const { container } = render(
			<PageShell spacing="space-y-2">
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('space-y-2');
		expect(getShell(container).className).not.toContain('space-y-6');
	});

	it('appends a custom className', () => {
		const { container } = render(
			<PageShell className="custom-shell">
				<p>x</p>
			</PageShell>,
		);
		expect(getShell(container).className).toContain('custom-shell');
	});
});
