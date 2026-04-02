import { render, screen, fireEvent } from '@testing-library/react';
import { useRef, useState } from 'react';
import axe from 'axe-core';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
	if (shouldThrow) throw new Error('Boom');
	return <p>All good</p>;
}

function RecoverableScenario() {
	const throwRef = useRef(true);
	const [, forceUpdate] = useState(0);

	return (
		<>
			<button
				onClick={() => {
					throwRef.current = false;
					forceUpdate((n) => n + 1);
				}}
			>
				Stop throwing
			</button>
			<ErrorBoundary>
				<ThrowingChild shouldThrow={throwRef.current} />
			</ErrorBoundary>
		</>
	);
}

beforeEach(() => {
	vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe('ErrorBoundary', () => {
	it('renders children when there is no error', () => {
		render(
			<ErrorBoundary>
				<ThrowingChild shouldThrow={false} />
			</ErrorBoundary>,
		);
		expect(screen.getByText('All good')).toBeInTheDocument();
	});

	it('renders default fallback UI on error', () => {
		render(
			<ErrorBoundary>
				<ThrowingChild shouldThrow={true} />
			</ErrorBoundary>,
		);
		expect(screen.getByText('Something went wrong')).toBeInTheDocument();
		expect(screen.getByText('Boom')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
	});

	it('renders custom fallback when provided', () => {
		render(
			<ErrorBoundary fallback={<div>Custom error</div>}>
				<ThrowingChild shouldThrow={true} />
			</ErrorBoundary>,
		);
		expect(screen.getByText('Custom error')).toBeInTheDocument();
		expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
	});

	it('recovers when Try again is clicked', () => {
		render(<RecoverableScenario />);
		expect(screen.getByText('Something went wrong')).toBeInTheDocument();

		fireEvent.click(screen.getByText('Stop throwing'));
		fireEvent.click(screen.getByRole('button', { name: /try again/i }));

		expect(screen.getByText('All good')).toBeInTheDocument();
	});

	it('resets error when resetKey changes', () => {
		const { rerender } = render(
			<ErrorBoundary resetKey="/page-a">
				<ThrowingChild shouldThrow={true} />
			</ErrorBoundary>,
		);
		expect(screen.getByText('Something went wrong')).toBeInTheDocument();

		rerender(
			<ErrorBoundary resetKey="/page-b">
				<ThrowingChild shouldThrow={false} />
			</ErrorBoundary>,
		);
		expect(screen.getByText('All good')).toBeInTheDocument();
	});

	it('default fallback has no accessibility violations', async () => {
		const { container } = render(
			<ErrorBoundary>
				<ThrowingChild shouldThrow={true} />
			</ErrorBoundary>,
		);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});
});
