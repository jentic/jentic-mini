import { render, screen, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import { Input } from '@/components/ui/Input';

describe('Input', () => {
	it('renders and accepts user input', () => {
		render(<Input placeholder="Enter name" />);
		const input = screen.getByPlaceholderText('Enter name');
		fireEvent.change(input, { target: { value: 'Alice' } });
		expect(input).toHaveValue('Alice');
	});

	it('forwards ref to underlying input element', () => {
		const ref = createRef<HTMLInputElement>();
		render(<Input ref={ref} />);
		expect(ref.current).toBeInstanceOf(HTMLInputElement);
	});

	it('shows error message with role="alert" when error prop is set', () => {
		render(<Input error="Required field" />);
		expect(screen.getByRole('alert')).toHaveTextContent('Required field');
	});

	it('sets aria-invalid when error is provided', () => {
		render(<Input error="Invalid" placeholder="Email" />);
		expect(screen.getByPlaceholderText('Email')).toHaveAttribute('aria-invalid', 'true');
	});

	it('does not set aria-invalid when there is no error', () => {
		render(<Input placeholder="Email" />);
		expect(screen.getByPlaceholderText('Email')).not.toHaveAttribute('aria-invalid');
	});

	it('toggles password visibility when showPasswordToggle is true', () => {
		render(<Input type="password" showPasswordToggle />);
		const toggleButton = screen.getByRole('button', { name: 'Show password' });

		fireEvent.click(toggleButton);
		expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument();

		fireEvent.click(screen.getByRole('button', { name: 'Hide password' }));
		expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
	});

	it('passes native HTML attributes through', () => {
		render(<Input placeholder="Search..." disabled data-testid="my-input" />);
		const input = screen.getByTestId('my-input');
		expect(input).toBeDisabled();
		expect(input).toHaveAttribute('placeholder', 'Search...');
	});

	it('uses provided id over generated id', () => {
		render(<Input id="custom-id" />);
		expect(document.getElementById('custom-id')).toBeInstanceOf(HTMLInputElement);
	});

	it('connects error message to input via aria-describedby', () => {
		render(<Input id="email" error="Invalid email" />);
		const input = document.getElementById('email')!;
		const errorId = input.getAttribute('aria-describedby');
		expect(errorId).toBe('email-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'email-error');
	});
});
