import { render, screen, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
import { Dialog } from '@/components/ui/Dialog';

describe('Dialog', () => {
	let showModalSpy: ReturnType<typeof vi.spyOn>;
	let closeSpy: ReturnType<typeof vi.spyOn>;

	beforeEach(() => {
		showModalSpy = vi
			.spyOn(HTMLDialogElement.prototype, 'showModal')
			.mockImplementation(() => {});
		closeSpy = vi.spyOn(HTMLDialogElement.prototype, 'close').mockImplementation(() => {});
	});

	afterEach(() => {
		showModalSpy.mockRestore();
		closeSpy.mockRestore();
	});

	it('calls showModal when open transitions to true', () => {
		const { rerender } = render(
			<Dialog open={false} onClose={vi.fn()} title="Test">
				Content
			</Dialog>,
		);
		expect(showModalSpy).not.toHaveBeenCalled();

		rerender(
			<Dialog open={true} onClose={vi.fn()} title="Test">
				Content
			</Dialog>,
		);
		expect(showModalSpy).toHaveBeenCalledOnce();
	});

	it('calls close when open transitions to false after being open', () => {
		const { rerender } = render(
			<Dialog open={true} onClose={vi.fn()} title="Test">
				Content
			</Dialog>,
		);

		Object.defineProperty(document.querySelector('dialog')!, 'open', {
			value: true,
			writable: true,
		});

		rerender(
			<Dialog open={false} onClose={vi.fn()} title="Test">
				Content
			</Dialog>,
		);
		expect(closeSpy).toHaveBeenCalledOnce();
	});

	it('renders title, children, and footer', () => {
		render(
			<Dialog open={true} onClose={vi.fn()} title="Confirm" footer={<button>Save</button>}>
				Body text
			</Dialog>,
		);
		const dialog = document.querySelector('dialog')!;
		expect(dialog.querySelector('h2')).toHaveTextContent('Confirm');
		expect(screen.getByText('Body text')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: 'Save', hidden: true })).toBeInTheDocument();
	});

	it('calls onClose when close button is clicked', () => {
		const onClose = vi.fn();
		render(
			<Dialog open={true} onClose={onClose} title="Test">
				Content
			</Dialog>,
		);
		fireEvent.click(screen.getByRole('button', { name: 'Close', hidden: true }));
		expect(onClose).toHaveBeenCalledOnce();
	});

	it('calls onClose on cancel event (Escape key)', () => {
		const onClose = vi.fn();
		render(
			<Dialog open={true} onClose={onClose} title="Test">
				Content
			</Dialog>,
		);
		const dialog = document.querySelector('dialog')!;
		dialog.dispatchEvent(new Event('cancel', { bubbles: true }));
		expect(onClose).toHaveBeenCalledOnce();
	});

	it('has aria-labelledby pointing to the title', () => {
		render(
			<Dialog open={true} onClose={vi.fn()} title="My Title">
				Content
			</Dialog>,
		);
		const dialog = document.querySelector('dialog')!;
		const titleId = dialog.getAttribute('aria-labelledby');
		expect(titleId).toBeTruthy();
		expect(document.getElementById(titleId!)).toHaveTextContent('My Title');
	});

	it('has no accessibility violations', async () => {
		const { container } = render(
			<Dialog open={true} onClose={vi.fn()} title="Accessible Dialog">
				Dialog content
			</Dialog>,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
