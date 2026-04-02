import { render, screen, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
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

	it('shows error with role="alert" and sets aria-invalid', () => {
		render(<Input error="Required field" placeholder="Email" />);
		expect(screen.getByRole('alert')).toHaveTextContent('Required field');
		expect(screen.getByPlaceholderText('Email')).toHaveAttribute('aria-invalid', 'true');
	});

	it('connects error message to input via aria-describedby', () => {
		render(<Input id="email" error="Invalid email" />);
		const input = document.getElementById('email')!;
		expect(input).toHaveAttribute('aria-describedby', 'email-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'email-error');
	});

	it('toggles password visibility', () => {
		render(<Input type="password" showPasswordToggle />);
		fireEvent.click(screen.getByRole('button', { name: 'Show password' }));
		expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument();
	});

	it('passes native HTML attributes through', () => {
		render(<Input placeholder="Search..." disabled />);
		expect(screen.getByPlaceholderText('Search...')).toBeDisabled();
	});

	it('has no accessibility violations', async () => {
		const { container } = render(
			<label htmlFor="test-input">
				Name
				<Input id="test-input" />
			</label>,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
