import { render, screen } from '@testing-library/react';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

describe('ErrorAlert', () => {
	it('renders message text', () => {
		render(<ErrorAlert message="Something went wrong." />);
		expect(screen.getByText('Something went wrong.')).toBeInTheDocument();
	});

	it('has role="alert" for accessibility', () => {
		render(<ErrorAlert message="Something went wrong." />);
		expect(screen.getByRole('alert')).toBeInTheDocument();
	});

	it('renders an icon', () => {
		render(<ErrorAlert message="Something went wrong." />);
		const alert = screen.getByRole('alert');
		expect(alert.querySelector('svg')).toBeTruthy();
	});
});
