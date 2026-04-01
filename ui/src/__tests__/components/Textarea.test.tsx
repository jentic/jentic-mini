import { render, screen, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import { Textarea } from '@/components/ui/Textarea';

describe('Textarea', () => {
	it('renders and accepts text input', () => {
		render(<Textarea placeholder="Write something..." />);
		const textarea = screen.getByPlaceholderText('Write something...');
		fireEvent.change(textarea, { target: { value: 'Hello world' } });
		expect(textarea).toHaveValue('Hello world');
	});

	it('forwards ref to underlying textarea element', () => {
		const ref = createRef<HTMLTextAreaElement>();
		render(<Textarea ref={ref} />);
		expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
	});

	it('shows error message with role="alert" when error prop is set', () => {
		render(<Textarea error="Too short" />);
		expect(screen.getByRole('alert')).toHaveTextContent('Too short');
	});

	it('sets aria-invalid when error is provided', () => {
		render(<Textarea error="Required" placeholder="Bio" />);
		expect(screen.getByPlaceholderText('Bio')).toHaveAttribute('aria-invalid', 'true');
	});

	it('does not set aria-invalid when there is no error', () => {
		render(<Textarea placeholder="Bio" />);
		expect(screen.getByPlaceholderText('Bio')).not.toHaveAttribute('aria-invalid');
	});

	it('passes native textarea attributes through', () => {
		render(<Textarea rows={5} placeholder="Notes" disabled data-testid="my-textarea" />);
		const textarea = screen.getByTestId('my-textarea');
		expect(textarea).toBeDisabled();
		expect(textarea).toHaveAttribute('rows', '5');
		expect(textarea).toHaveAttribute('placeholder', 'Notes');
	});

	it('connects error message to textarea via aria-describedby', () => {
		render(<Textarea id="bio" error="Too long" />);
		const textarea = document.getElementById('bio')!;
		const errorId = textarea.getAttribute('aria-describedby');
		expect(errorId).toBe('bio-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'bio-error');
	});
});
