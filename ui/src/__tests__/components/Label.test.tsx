import { render, screen } from '@testing-library/react';
import { Label } from '@/components/ui/Label';

describe('Label', () => {
	it('renders children text', () => {
		render(<Label>Username</Label>);
		expect(screen.getByText('Username')).toBeInTheDocument();
	});

	it('applies htmlFor attribute', () => {
		render(<Label htmlFor="email-input">Email</Label>);
		expect(screen.getByText('Email')).toHaveAttribute('for', 'email-input');
	});

	it('shows required visual indicator via CSS when required is true', () => {
		const { container } = render(<Label required>Name</Label>);
		const label = container.querySelector('label');
		expect(label?.className).toMatch(/after:content-\['\*'\]/);
	});

	it('does not show required indicator when required is false', () => {
		const { container } = render(<Label>Name</Label>);
		const label = container.querySelector('label');
		expect(label?.className).not.toMatch(/after:content-\['\*'\]/);
	});

	it('passes through additional props', () => {
		render(<Label data-testid="my-label">Field</Label>);
		expect(screen.getByTestId('my-label')).toBeInTheDocument();
	});
});
