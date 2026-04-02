import { render, screen, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
import { createRef } from 'react';
import { Select } from '@/components/ui/Select';

describe('Select', () => {
	it('renders with option children', () => {
		render(
			<label htmlFor="color-select">
				Color
				<Select id="color-select">
					<option value="red">Red</option>
					<option value="blue">Blue</option>
				</Select>
			</label>,
		);
		expect(screen.getByRole('option', { name: 'Red' })).toBeInTheDocument();
		expect(screen.getByRole('option', { name: 'Blue' })).toBeInTheDocument();
	});

	it('forwards ref', () => {
		const ref = createRef<HTMLSelectElement>();
		render(
			<Select ref={ref}>
				<option value="a">A</option>
			</Select>,
		);
		expect(ref.current).toBeInstanceOf(HTMLSelectElement);
	});

	it('fires onChange when selection changes', () => {
		const onChange = vi.fn();
		render(
			<label htmlFor="fruit-select">
				Fruit
				<Select id="fruit-select" onChange={onChange}>
					<option value="apple">Apple</option>
					<option value="banana">Banana</option>
				</Select>
			</label>,
		);
		fireEvent.change(screen.getByRole('combobox'), { target: { value: 'banana' } });
		expect(onChange).toHaveBeenCalledOnce();
	});

	it('shows error with role="alert" and sets aria-invalid', () => {
		render(
			<label htmlFor="err-select">
				Role
				<Select id="err-select" error="Required">
					<option value="">Pick one</option>
				</Select>
			</label>,
		);
		expect(screen.getByRole('alert')).toHaveTextContent('Required');
		expect(screen.getByRole('combobox')).toHaveAttribute('aria-invalid', 'true');
	});

	it('connects error message to select via aria-describedby', () => {
		render(
			<Select id="role" error="Invalid role">
				<option value="">Choose role</option>
			</Select>,
		);
		const select = document.getElementById('role')!;
		expect(select).toHaveAttribute('aria-describedby', 'role-error');
		expect(screen.getByRole('alert')).toHaveAttribute('id', 'role-error');
	});

	it('has no accessibility violations', async () => {
		const { container } = render(
			<label htmlFor="test-select">
				Color
				<Select id="test-select">
					<option value="red">Red</option>
				</Select>
			</label>,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
