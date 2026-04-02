import { render, screen } from '@testing-library/react';
import { Label } from '@/components/ui/Label';

describe('Label', () => {
	it('renders children and applies htmlFor', () => {
		render(<Label htmlFor="email">Email</Label>);
		const label = screen.getByText('Email');
		expect(label).toHaveAttribute('for', 'email');
	});

	it('does not include required indicator in accessible text', () => {
		render(<Label required>Username</Label>);
		const label = screen.getByText('Username');
		expect(label.textContent).toBe('Username');
	});
});
