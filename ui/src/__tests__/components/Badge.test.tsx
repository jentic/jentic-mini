import { render, screen } from '@testing-library/react';
import { Badge, MethodBadge, StatusBadge } from '@/components/ui/Badge';

describe('Badge', () => {
	it('renders children text', () => {
		render(<Badge>active</Badge>);
		expect(screen.getByText('active')).toBeInTheDocument();
	});

	it('renders with each variant without crashing', () => {
		const variants = ['default', 'success', 'warning', 'danger', 'pending'] as const;
		for (const variant of variants) {
			const { unmount } = render(<Badge variant={variant}>{variant}</Badge>);
			expect(screen.getByText(variant)).toBeInTheDocument();
			unmount();
		}
	});

	it('applies custom className', () => {
		render(<Badge className="my-custom">test</Badge>);
		expect(screen.getByText('test').className).toContain('my-custom');
	});

	it('spreads additional HTML attributes', () => {
		render(<Badge data-testid="badge-test">test</Badge>);
		expect(screen.getByTestId('badge-test')).toBeInTheDocument();
	});
});

describe('MethodBadge', () => {
	it('renders the HTTP method in uppercase', () => {
		render(<MethodBadge method="get" />);
		expect(screen.getByText('GET')).toBeInTheDocument();
	});

	it.each(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])('renders %s correctly', (method) => {
		const { unmount } = render(<MethodBadge method={method.toLowerCase()} />);
		expect(screen.getByText(method)).toBeInTheDocument();
		unmount();
	});

	it('shows "?" when method is null', () => {
		render(<MethodBadge method={null} />);
		expect(screen.getByText('?')).toBeInTheDocument();
	});

	it('shows "?" when method is undefined', () => {
		render(<MethodBadge />);
		expect(screen.getByText('?')).toBeInTheDocument();
	});

	it('uses fallback style for unknown methods', () => {
		render(<MethodBadge method="OPTIONS" />);
		expect(screen.getByText('OPTIONS')).toBeInTheDocument();
	});
});

describe('StatusBadge', () => {
	it('renders the status code', () => {
		render(<StatusBadge status={200} />);
		expect(screen.getByText('200')).toBeInTheDocument();
	});

	it('returns null for falsy status', () => {
		const { container } = render(<StatusBadge status={null} />);
		expect(container).toBeEmptyDOMElement();
	});

	it('returns null for zero status', () => {
		const { container } = render(<StatusBadge status={0} />);
		expect(container).toBeEmptyDOMElement();
	});

	it.each([
		[200, 'success'],
		[201, 'success'],
		[299, 'success'],
		[400, 'warning'],
		[404, 'warning'],
		[500, 'danger'],
		[503, 'danger'],
		[301, 'default'],
	])('renders %i with correct variant', (status, _variant) => {
		const { unmount } = render(<StatusBadge status={status} />);
		expect(screen.getByText(String(status))).toBeInTheDocument();
		unmount();
	});
});
