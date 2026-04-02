import { render, screen, fireEvent } from '@testing-library/react';
import { Pagination } from '@/components/ui/Pagination';

describe('Pagination', () => {
	it('displays page info and disables buttons at boundaries', () => {
		render(<Pagination page={1} totalPages={5} onPageChange={vi.fn()} />);
		expect(screen.getByText('Page 1 of 5')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
		expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled();
	});

	it('calls onPageChange with correct page numbers', () => {
		const onPageChange = vi.fn();
		render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);

		fireEvent.click(screen.getByRole('button', { name: /previous/i }));
		expect(onPageChange).toHaveBeenCalledWith(2);

		fireEvent.click(screen.getByRole('button', { name: /next/i }));
		expect(onPageChange).toHaveBeenCalledWith(4);
	});

	it('returns null when totalPages <= 0', () => {
		const { container } = render(<Pagination page={1} totalPages={0} onPageChange={vi.fn()} />);
		expect(container.firstChild).toBeNull();
	});
});
