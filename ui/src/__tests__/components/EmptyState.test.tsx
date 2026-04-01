import { render, screen } from '@testing-library/react';
import { EmptyState } from '@/components/ui/EmptyState';

const FakeIcon = () => <svg data-testid="empty-icon" />;

describe('EmptyState', () => {
	it('renders icon, title, and description', () => {
		render(
			<EmptyState
				icon={<FakeIcon />}
				title="Nothing here"
				description="Try adding some items."
			/>,
		);

		expect(screen.getByTestId('empty-icon')).toBeInTheDocument();
		expect(screen.getByText('Nothing here')).toBeInTheDocument();
		expect(screen.getByText('Try adding some items.')).toBeInTheDocument();
	});

	it('renders without description when not provided', () => {
		render(<EmptyState icon={<FakeIcon />} title="Nothing here" />);

		expect(screen.getByText('Nothing here')).toBeInTheDocument();
		expect(screen.queryByText('Try adding some items.')).not.toBeInTheDocument();
	});

	it('renders action slot when provided', () => {
		render(
			<EmptyState
				icon={<FakeIcon />}
				title="Nothing here"
				action={<button>Add item</button>}
			/>,
		);

		expect(screen.getByRole('button', { name: 'Add item' })).toBeInTheDocument();
	});

	it('does not render action slot when not provided', () => {
		render(<EmptyState icon={<FakeIcon />} title="Nothing here" />);

		expect(screen.queryByRole('button')).not.toBeInTheDocument();
	});
});
