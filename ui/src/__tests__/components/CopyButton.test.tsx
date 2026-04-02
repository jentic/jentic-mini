import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CopyButton } from '@/components/ui/CopyButton';

let writeTextSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
	writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
});

afterEach(() => {
	writeTextSpy.mockRestore();
});

describe('CopyButton', () => {
	it('copies value to clipboard and shows feedback', async () => {
		render(<CopyButton value="secret-key" label="Copy" />);
		fireEvent.click(screen.getByRole('button', { name: 'Copy' }));

		await waitFor(() => {
			expect(writeTextSpy).toHaveBeenCalledWith('secret-key');
			expect(screen.getByText('Copied!')).toBeInTheDocument();
		});
	});

	it('renders icon-only when no label is provided', () => {
		render(<CopyButton value="abc" />);
		const button = screen.getByRole('button');
		expect(button.querySelector('svg')).toBeTruthy();
		expect(button.textContent).toBe('');
	});
});
