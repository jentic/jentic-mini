import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BackButton } from '@/components/ui/BackButton';

describe('BackButton', () => {
	it('renders as a link with correct href', () => {
		render(
			<MemoryRouter>
				<BackButton to="/dashboard" label="Back to dashboard" />
			</MemoryRouter>,
		);

		const link = screen.getByRole('link', { name: /Back to dashboard/i });
		expect(link).toBeInTheDocument();
		expect(link).toHaveAttribute('href', '/dashboard');
	});

	it('displays the label text', () => {
		render(
			<MemoryRouter>
				<BackButton to="/test" label="Go back" />
			</MemoryRouter>,
		);

		expect(screen.getByText('Go back')).toBeInTheDocument();
	});
});
