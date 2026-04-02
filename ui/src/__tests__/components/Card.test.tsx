import { render, screen, fireEvent } from '@testing-library/react';
import { Card, CardHeader, CardBody, CardTitle, CardFooter } from '@/components/ui/Card';

describe('Card', () => {
	it('renders children', () => {
		render(<Card>Card content</Card>);
		expect(screen.getByText('Card content')).toBeInTheDocument();
	});

	it('calls onClick when clicked', () => {
		const onClick = vi.fn();
		render(<Card onClick={onClick}>Clickable</Card>);
		fireEvent.click(screen.getByText('Clickable'));
		expect(onClick).toHaveBeenCalledOnce();
	});

	it('applies hoverable cursor-pointer class', () => {
		const { container } = render(<Card hoverable>Hoverable</Card>);
		expect(container.firstElementChild!.className).toContain('cursor-pointer');
	});

	it('does not apply cursor-pointer when not hoverable', () => {
		const { container } = render(<Card>Static</Card>);
		expect(container.firstElementChild!.className).not.toContain('cursor-pointer');
	});

	it('applies custom className', () => {
		const { container } = render(<Card className="my-card">test</Card>);
		expect(container.firstElementChild!.className).toContain('my-card');
	});
});

describe('CardHeader', () => {
	it('renders children', () => {
		render(<CardHeader>Header</CardHeader>);
		expect(screen.getByText('Header')).toBeInTheDocument();
	});
});

describe('CardBody', () => {
	it('renders children', () => {
		render(<CardBody>Body</CardBody>);
		expect(screen.getByText('Body')).toBeInTheDocument();
	});
});

describe('CardFooter', () => {
	it('renders children', () => {
		render(<CardFooter>Footer content</CardFooter>);
		expect(screen.getByText('Footer content')).toBeInTheDocument();
	});

	it('applies custom className', () => {
		const { container } = render(<CardFooter className="custom-footer">test</CardFooter>);
		expect(container.firstElementChild!.className).toContain('custom-footer');
	});
});

describe('CardTitle', () => {
	it('renders as an h3 heading', () => {
		render(<CardTitle>My Title</CardTitle>);
		expect(screen.getByRole('heading', { level: 3, name: 'My Title' })).toBeInTheDocument();
	});
});
