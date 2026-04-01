import { render, screen, fireEvent } from '@testing-library/react';
import { createRef } from 'react';
import { Select } from '@/components/ui/Select';

describe('Select', () => {
	it('renders with children option elements', () => {
		render(
			<Select data-testid="color-select">
				<option value="red">Red</option>
				<option value="blue">Blue</option>
			</Select>,
		);
		const select = screen.getByTestId('color-select');
		expect(select).toBeInTheDocument();
		expect(screen.getByRole('option', { name: 'Red' })).toBeInTheDocument();
		expect(screen.getByRole('option', { name: 'Blue' })).toBeInTheDocument();
	});

	it('forwards ref to underlying select element', () => {
		const ref = createRef<HTMLSelectElement>();
		render(
			<Select ref={ref}>
				<option value="a">A</option>
			</Select>,
		);
		expect(ref.current).toBeInstanceOf(HTMLSelectElement);
	});

	it('shows error message with role="alert" when error prop is set', () => {
		render(
			<Select error="Please select an option">
				<option value="">Choose</option>
			</Select>,
		);
		expect(screen.getByRole('alert')).toHaveTextContent('Please select an option');
	});

	it('fires onChange when selection changes', () => {
		const onChange = vi.fn();
		render(
			<Select onChange={onChange} data-testid="fruit-select">
				<option value="apple">Apple</option>
				<option value="banana">Banana</option>
			</Select>,
		);
		fireEvent.change(screen.getByTestId('fruit-select'), { target: { value: 'banana' } });
		expect(onChange).toHaveBeenCalledOnce();
	});

	it('sets aria-invalid when error is provided', () => {
		render(
			<Select error="Required" data-testid="err-select">
				<option value="">Pick one</option>
			</Select>,
		);
		expect(screen.getByTestId('err-select')).toHaveAttribute('aria-invalid', 'true');
	});

	it('does not set aria-invalid when there is no error', () => {
		render(
			<Select data-testid="ok-select">
				<option value="x">X</option>
			</Select>,
		);
		expect(screen.getByTestId('ok-select')).not.toHaveAttribute('aria-invalid');
	});

	it('connects error message to select via aria-describedby', () => {
		render(
			<Select id="role" error="Invalid role">
				<option value="">Choose role</option>
			</Select>,
		);
		const select = document.getElementById('role')!;
		const errorId = select.getAttribute('aria-describedby');
		expect(errorId).toBe('role-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'role-error');
	});
});
