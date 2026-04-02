import { createRef } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
import { Button } from '@/components/ui/Button';

describe('Button', () => {
	it('renders children text', () => {
		render(<Button>Save</Button>);
		expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
	});

	it('fires onClick when clicked', () => {
		const onClick = vi.fn();
		render(<Button onClick={onClick}>Click me</Button>);
		fireEvent.click(screen.getByRole('button'));
		expect(onClick).toHaveBeenCalledOnce();
	});

	it('is disabled when disabled prop is true', () => {
		render(<Button disabled>Save</Button>);
		expect(screen.getByRole('button')).toBeDisabled();
	});

	it('is disabled when loading prop is true', () => {
		render(<Button loading>Save</Button>);
		expect(screen.getByRole('button')).toBeDisabled();
	});

	it('shows a spinner when loading', () => {
		render(<Button loading>Save</Button>);
		const button = screen.getByRole('button');
		expect(button.querySelector('svg')).toBeTruthy();
	});

	it('does not fire onClick when loading', () => {
		const onClick = vi.fn();
		render(
			<Button loading onClick={onClick}>
				Save
			</Button>,
		);
		fireEvent.click(screen.getByRole('button'));
		expect(onClick).not.toHaveBeenCalled();
	});

	it('forwards additional HTML attributes', () => {
		render(
			<Button type="submit" data-testid="submit-btn">
				Go
			</Button>,
		);
		const button = screen.getByTestId('submit-btn');
		expect(button).toHaveAttribute('type', 'submit');
	});

	it('forwards ref to the button element', () => {
		const ref = createRef<HTMLButtonElement>();
		render(<Button ref={ref}>Ref</Button>);
		expect(ref.current).toBeInstanceOf(HTMLButtonElement);
		expect(ref.current!.textContent).toBe('Ref');
	});

	it('renders with each variant without crashing', () => {
		const variants = ['primary', 'secondary', 'danger', 'ghost', 'outline'] as const;
		for (const variant of variants) {
			const { unmount } = render(<Button variant={variant}>{variant}</Button>);
			expect(screen.getByRole('button', { name: variant })).toBeInTheDocument();
			unmount();
		}
	});

	it('renders with each size without crashing', () => {
		const sizes = ['sm', 'md', 'lg', 'icon'] as const;
		for (const size of sizes) {
			const { unmount } = render(<Button size={size}>btn</Button>);
			expect(screen.getByRole('button')).toBeInTheDocument();
			unmount();
		}
	});

	it('applies fullWidth class', () => {
		render(<Button fullWidth>Full</Button>);
		expect(screen.getByRole('button').className).toContain('w-full');
	});

	it('sets aria-busy when loading', () => {
		render(<Button loading>Save</Button>);
		expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
	});

	it('defaults to type="button"', () => {
		render(<Button>Default</Button>);
		expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
	});

	it('has no accessibility violations', async () => {
		const { container } = render(<Button>Accessible</Button>);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
