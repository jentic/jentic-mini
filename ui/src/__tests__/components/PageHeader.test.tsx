import { render, screen } from '@testing-library/react';
import { PageHeader } from '@/components/ui/PageHeader';

describe('PageHeader', () => {
	it('renders title as h1 heading', () => {
		render(<PageHeader title="Dashboard" />);
		expect(screen.getByRole('heading', { name: 'Dashboard', level: 1 })).toBeInTheDocument();
	});

	it('renders category when provided', () => {
		render(<PageHeader category="Admin" title="Dashboard" />);
		expect(screen.getByText('Admin')).toBeInTheDocument();
	});

	it('renders description when provided', () => {
		render(<PageHeader title="Dashboard" description="Overview of your system." />);
		expect(screen.getByText('Overview of your system.')).toBeInTheDocument();
	});

	it('renders actions slot', () => {
		render(<PageHeader title="Dashboard" actions={<button>Export</button>} />);
		expect(screen.getByRole('button', { name: 'Export' })).toBeInTheDocument();
	});
});
