import { render, screen } from '@testing-library/react';
import { PermissionRuleDisplay } from '@/components/ui/PermissionRuleDisplay';
import type { PermissionRule } from '@/api/types';

describe('PermissionRuleDisplay', () => {
	it('shows empty message when no rules', () => {
		render(<PermissionRuleDisplay rules={[]} />);
		expect(screen.getByText(/no permission rules/i)).toBeInTheDocument();
	});

	it('renders system rule description', () => {
		const rules: PermissionRule[] = [{ effect: 'allow', _system: true }];
		render(<PermissionRuleDisplay rules={rules} />);
		expect(screen.getByText('System rule (managed automatically)')).toBeInTheDocument();
	});

	it('renders allow rule with path and methods', () => {
		const rules: PermissionRule[] = [
			{ effect: 'allow', path: '/api/*', methods: ['GET', 'POST'] },
		];
		render(<PermissionRuleDisplay rules={rules} />);
		expect(screen.getByText('Allow GET, POST requests to /api/*')).toBeInTheDocument();
	});

	it('renders deny rule with operations', () => {
		const rules: PermissionRule[] = [{ effect: 'deny', operations: ['deleteUser', 'resetDb'] }];
		render(<PermissionRuleDisplay rules={rules} />);
		expect(screen.getByText('Deny operations: deleteUser, resetDb')).toBeInTheDocument();
	});

	it('renders "all requests" when no path or operations', () => {
		const rules: PermissionRule[] = [{ effect: 'allow' }];
		render(<PermissionRuleDisplay rules={rules} />);
		expect(screen.getByText('Allow all requests')).toBeInTheDocument();
	});

	it('renders "any method" when path set but no methods', () => {
		const rules: PermissionRule[] = [{ effect: 'deny', path: '/admin' }];
		render(<PermissionRuleDisplay rules={rules} />);
		expect(screen.getByText('Deny any method requests to /admin')).toBeInTheDocument();
	});
});
