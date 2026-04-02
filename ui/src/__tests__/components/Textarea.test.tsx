import { render, screen, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
import { createRef } from 'react';
import { Textarea } from '@/components/ui/Textarea';

describe('Textarea', () => {
	it('renders and accepts text input', () => {
		render(<Textarea placeholder="Write something..." />);
		const textarea = screen.getByPlaceholderText('Write something...');
		fireEvent.change(textarea, { target: { value: 'Hello world' } });
		expect(textarea).toHaveValue('Hello world');
	});

	it('forwards ref', () => {
		const ref = createRef<HTMLTextAreaElement>();
		render(<Textarea ref={ref} />);
		expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
	});

	it('shows error with role="alert" and sets aria-invalid', () => {
		render(<Textarea error="Too short" placeholder="Bio" />);
		expect(screen.getByRole('alert')).toHaveTextContent('Too short');
		expect(screen.getByPlaceholderText('Bio')).toHaveAttribute('aria-invalid', 'true');
	});

	it('connects error message to textarea via aria-describedby', () => {
		render(<Textarea id="bio" error="Too long" />);
		const textarea = document.getElementById('bio')!;
		expect(textarea).toHaveAttribute('aria-describedby', 'bio-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'bio-error');
	});

	it('passes native attributes through', () => {
		render(<Textarea rows={5} placeholder="Notes" disabled />);
		const textarea = screen.getByPlaceholderText('Notes');
		expect(textarea).toBeDisabled();
		expect(textarea).toHaveAttribute('rows', '5');
	});

	it('has no accessibility violations', async () => {
		const { container } = render(
			<label htmlFor="test-textarea">
				Bio
				<Textarea id="test-textarea" />
			</label>,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
