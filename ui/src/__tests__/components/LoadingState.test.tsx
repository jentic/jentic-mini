import { render, screen } from '@testing-library/react';
import { LoadingState } from '@/components/ui/LoadingState';

describe('LoadingState', () => {
	it('renders default "Loading..." message', () => {
		render(<LoadingState />);
		expect(screen.getByText('Loading...')).toBeInTheDocument();
	});

	it('renders custom message', () => {
		render(<LoadingState message="Fetching results..." />);
		expect(screen.getByText('Fetching results...')).toBeInTheDocument();
		expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
	});

	it('renders custom icon when provided', () => {
		render(<LoadingState icon={<svg data-testid="custom-icon" />} />);
		expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
	});
});
