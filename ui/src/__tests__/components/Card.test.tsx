import { render, screen, fireEvent } from '@testing-library/react';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';

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

describe('CardTitle', () => {
	it('renders as an h3 heading', () => {
		render(<CardTitle>My Title</CardTitle>);
		expect(screen.getByRole('heading', { level: 3, name: 'My Title' })).toBeInTheDocument();
	});
});
