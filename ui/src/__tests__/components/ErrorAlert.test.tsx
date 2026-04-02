import { render, screen } from '@testing-library/react';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

describe('ErrorAlert', () => {
	it('renders message with role="alert" and icon', () => {
		render(<ErrorAlert message="Something went wrong." />);
		const alert = screen.getByRole('alert');
		expect(alert).toHaveTextContent('Something went wrong.');
		expect(alert.querySelector('svg')).toBeTruthy();
	});
});
