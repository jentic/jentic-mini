import { useCallback, useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MenuPanel, MenuSeparator, menuItemClass, useDismissable } from '@/components/ui/Menu';

function DismissableHarness({ initialOpen = true }: { initialOpen?: boolean }) {
	const [open, setOpen] = useState(initialOpen);
	const close = useCallback(() => setOpen(false), []);
	const ref = useDismissable<HTMLDivElement>(open, close);
	return (
		<>
			<button data-testid="outside">outside</button>
			<div ref={ref} data-testid="container">
				<button data-testid="inside">inside</button>
				{open && <div data-testid="panel">panel</div>}
			</div>
		</>
	);
}

describe('useDismissable', () => {
	it('closes when clicking outside the container', () => {
		render(<DismissableHarness />);
		expect(screen.getByTestId('panel')).toBeInTheDocument();

		fireEvent.mouseDown(screen.getByTestId('outside'));

		expect(screen.queryByTestId('panel')).not.toBeInTheDocument();
	});

	it('does NOT close when clicking inside the container', () => {
		render(<DismissableHarness />);
		expect(screen.getByTestId('panel')).toBeInTheDocument();

		fireEvent.mouseDown(screen.getByTestId('inside'));

		expect(screen.getByTestId('panel')).toBeInTheDocument();
	});

	it('closes when pressing Escape', () => {
		render(<DismissableHarness />);
		expect(screen.getByTestId('panel')).toBeInTheDocument();

		fireEvent.keyDown(window, { key: 'Escape' });

		expect(screen.queryByTestId('panel')).not.toBeInTheDocument();
	});

	it('does NOT close on other keys', () => {
		render(<DismissableHarness />);

		fireEvent.keyDown(window, { key: 'Enter' });
		fireEvent.keyDown(window, { key: 'ArrowDown' });

		expect(screen.getByTestId('panel')).toBeInTheDocument();
	});

	it('listeners are not attached while closed', () => {
		render(<DismissableHarness initialOpen={false} />);
		expect(screen.queryByTestId('panel')).not.toBeInTheDocument();

		// Outside click + Escape with no panel rendered should not throw or
		// flip any state.
		fireEvent.mouseDown(screen.getByTestId('outside'));
		fireEvent.keyDown(window, { key: 'Escape' });

		expect(screen.queryByTestId('panel')).not.toBeInTheDocument();
	});
});

describe('MenuPanel', () => {
	it('renders with role="menu" and exposes children', () => {
		render(
			<MenuPanel>
				<span>child</span>
			</MenuPanel>,
		);
		const panel = screen.getByRole('menu');
		expect(panel).toBeInTheDocument();
		expect(panel.textContent).toContain('child');
	});

	it('aligns left by default', () => {
		render(<MenuPanel>x</MenuPanel>);
		expect(screen.getByRole('menu').className).toContain('left-0');
	});

	it('aligns right when align="right"', () => {
		render(<MenuPanel align="right">x</MenuPanel>);
		expect(screen.getByRole('menu').className).toContain('right-0');
	});

	it('appends custom className', () => {
		render(<MenuPanel className="custom-class">x</MenuPanel>);
		expect(screen.getByRole('menu').className).toContain('custom-class');
	});
});

describe('MenuSeparator', () => {
	it('renders an aria-hidden divider', () => {
		const { container } = render(<MenuSeparator />);
		const hr = container.querySelector('[aria-hidden="true"]');
		expect(hr).toBeInTheDocument();
		expect(hr?.className).toContain('h-px');
	});
});

describe('menuItemClass', () => {
	it('returns base + idle classes by default', () => {
		const cls = menuItemClass();
		const classes = cls.split(/\s+/);
		expect(cls).toContain('rounded-md');
		expect(cls).toContain('text-muted-foreground');
		expect(cls).toContain('hover:bg-muted');
		// `bg-muted` must NOT be applied on its own (idle state) — only via
		// the `hover:bg-muted` modifier. A substring check would falsely
		// match against `hover:bg-muted`, so we test the tokenised class
		// list directly.
		expect(classes).not.toContain('bg-muted');
	});

	it('switches to active variant when active=true', () => {
		const cls = menuItemClass(true);
		expect(cls).toContain('text-foreground');
		expect(cls).toContain('bg-muted');
	});
});
