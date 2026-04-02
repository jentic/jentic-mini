import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axe from 'axe-core';
import { OneTimeKeyDisplay } from '@/components/ui/OneTimeKeyDisplay';

let writeTextSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
	writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
});

afterEach(() => {
	writeTextSpy.mockRestore();
});

describe('OneTimeKeyDisplay', () => {
	it('displays the key value and warning', () => {
		render(<OneTimeKeyDisplay keyValue="jntc_secret_123" onConfirm={vi.fn()} />);
		expect(screen.getByText('jntc_secret_123')).toBeInTheDocument();
		expect(screen.getByText(/never be shown again/i)).toBeInTheDocument();
	});

	it('copies key to clipboard and shows feedback', async () => {
		render(<OneTimeKeyDisplay keyValue="jntc_abc" onConfirm={vi.fn()} />);
		fireEvent.click(screen.getByRole('button', { name: /copy/i }));

		await waitFor(() => {
			expect(writeTextSpy).toHaveBeenCalledWith('jntc_abc');
			expect(screen.getByText('Copied')).toBeInTheDocument();
		});
	});

	it('dismiss button is disabled until checkbox is checked', () => {
		const onConfirm = vi.fn();
		render(<OneTimeKeyDisplay keyValue="jntc_abc" onConfirm={onConfirm} />);

		const dismiss = screen.getByRole('button', { name: /dismiss/i });
		expect(dismiss).toBeDisabled();

		fireEvent.click(screen.getByRole('checkbox'));
		expect(dismiss).not.toBeDisabled();

		fireEvent.click(dismiss);
		expect(onConfirm).toHaveBeenCalledOnce();
	});

	it('renders custom title when provided', () => {
		render(
			<OneTimeKeyDisplay keyValue="key" onConfirm={vi.fn()} title="Toolkit Key Created" />,
		);
		expect(screen.getByText('Toolkit Key Created')).toBeInTheDocument();
	});

	it('has no accessibility violations', async () => {
		const { container } = render(
			<OneTimeKeyDisplay keyValue="jntc_test" onConfirm={vi.fn()} />,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
