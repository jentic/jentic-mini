import { render, screen, fireEvent } from '@testing-library/react';
import { Pagination } from '@/components/ui/Pagination';

describe('Pagination', () => {
	it('displays "Page X of Y"', () => {
		render(<Pagination page={2} totalPages={5} onPageChange={vi.fn()} />);
		expect(screen.getByText('Page 2 of 5')).toBeInTheDocument();
	});

	it('disables Previous on first page', () => {
		render(<Pagination page={1} totalPages={5} onPageChange={vi.fn()} />);
		expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
	});

	it('disables Next on last page', () => {
		render(<Pagination page={5} totalPages={5} onPageChange={vi.fn()} />);
		expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
	});

	it('calls onPageChange with correct page number for Previous', () => {
		const onPageChange = vi.fn();
		render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);

		fireEvent.click(screen.getByRole('button', { name: /previous/i }));
		expect(onPageChange).toHaveBeenCalledWith(2);
	});

	it('calls onPageChange with correct page number for Next', () => {
		const onPageChange = vi.fn();
		render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);

		fireEvent.click(screen.getByRole('button', { name: /next/i }));
		expect(onPageChange).toHaveBeenCalledWith(4);
	});

	it('returns null when totalPages <= 0', () => {
		const { container } = render(<Pagination page={1} totalPages={0} onPageChange={vi.fn()} />);
		expect(container.firstChild).toBeNull();
	});
});
