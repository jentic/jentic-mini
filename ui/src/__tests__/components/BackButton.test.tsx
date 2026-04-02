import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BackButton } from '@/components/ui/BackButton';

describe('BackButton', () => {
	it('renders as a link with correct href and label', () => {
		render(
			<MemoryRouter>
				<BackButton to="/dashboard" label="Back to dashboard" />
			</MemoryRouter>,
		);
		const link = screen.getByRole('link', { name: /Back to dashboard/i });
		expect(link).toHaveAttribute('href', '/dashboard');
	});
});
