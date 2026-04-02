import { render, screen } from '@testing-library/react';
import { LoadingState } from '@/components/ui/LoadingState';

describe('LoadingState', () => {
	it('renders default "Loading..." message', () => {
		render(<LoadingState />);
		expect(screen.getByText('Loading...')).toBeInTheDocument();
	});

	it('renders custom message and icon when provided', () => {
		render(<LoadingState message="Fetching..." icon={<svg data-testid="custom" />} />);
		expect(screen.getByText('Fetching...')).toBeInTheDocument();
		expect(screen.getByTestId('custom')).toBeInTheDocument();
	});
});
