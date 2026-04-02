import { render, screen, fireEvent } from '@testing-library/react';
import { PermissionRuleEditor } from '@/components/ui/PermissionRuleEditor';
import type { PermissionRule } from '@/api/types';

describe('PermissionRuleEditor', () => {
	it('renders existing rules with effect, path, and methods', () => {
		const rules: PermissionRule[] = [
			{ effect: 'allow', path: '/api/*', methods: ['GET', 'POST'] },
		];
		render(<PermissionRuleEditor rules={rules} onChange={vi.fn()} />);

		expect(screen.getByDisplayValue('/api/*')).toBeInTheDocument();
		expect(screen.getByDisplayValue('GET, POST')).toBeInTheDocument();
	});

	it('adds a new empty rule when "Add Rule" is clicked', () => {
		const onChange = vi.fn();
		render(<PermissionRuleEditor rules={[]} onChange={onChange} />);

		fireEvent.click(screen.getByRole('button', { name: /add rule/i }));
		expect(onChange).toHaveBeenCalledWith([{ effect: 'allow', path: '', methods: [] }]);
	});

	it('removes a rule when delete button is clicked', () => {
		const onChange = vi.fn();
		const rules: PermissionRule[] = [
			{ effect: 'allow', path: '/a', methods: [] },
			{ effect: 'deny', path: '/b', methods: [] },
		];
		render(<PermissionRuleEditor rules={rules} onChange={onChange} />);

		const deleteButtons = screen
			.getAllByRole('button')
			.filter((btn) => btn !== screen.getByRole('button', { name: /add rule/i }));
		fireEvent.click(deleteButtons[0]);
		expect(onChange).toHaveBeenCalledWith([{ effect: 'deny', path: '/b', methods: [] }]);
	});

	it('updates effect when select changes', () => {
		const onChange = vi.fn();
		const rules: PermissionRule[] = [{ effect: 'allow', path: '', methods: [] }];
		render(<PermissionRuleEditor rules={rules} onChange={onChange} />);

		fireEvent.change(screen.getByDisplayValue('Allow'), { target: { value: 'deny' } });
		expect(onChange).toHaveBeenCalledWith([{ effect: 'deny', path: '', methods: [] }]);
	});

	it('updates path when input changes', () => {
		const onChange = vi.fn();
		const rules: PermissionRule[] = [{ effect: 'allow', path: '', methods: [] }];
		render(<PermissionRuleEditor rules={rules} onChange={onChange} />);

		fireEvent.change(screen.getByPlaceholderText('/path/prefix or *'), {
			target: { value: '/api/v1' },
		});
		expect(onChange).toHaveBeenCalledWith([{ effect: 'allow', path: '/api/v1', methods: [] }]);
	});

	it('parses comma-separated methods and uppercases them', () => {
		const onChange = vi.fn();
		const rules: PermissionRule[] = [{ effect: 'allow', path: '', methods: [] }];
		render(<PermissionRuleEditor rules={rules} onChange={onChange} />);

		fireEvent.change(screen.getByPlaceholderText('GET, POST (blank=any)'), {
			target: { value: 'get, post, delete' },
		});
		expect(onChange).toHaveBeenCalledWith([
			{ effect: 'allow', path: '', methods: ['GET', 'POST', 'DELETE'] },
		]);
	});
});
