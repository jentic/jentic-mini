import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { createRef } from 'react';
import axe from 'axe-core';
import { AppLink } from '@/components/ui/AppLink';

function renderLink(ui: React.ReactElement, { route = '/' } = {}) {
	return render(ui, {
		wrapper: ({ children }) => <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>,
	});
}

describe('AppLink', () => {
	describe('internal links (React Router)', () => {
		it('renders a React Router Link for relative paths', () => {
			renderLink(<AppLink href="/dashboard">Dashboard</AppLink>);
			const link = screen.getByRole('link', { name: 'Dashboard' });
			expect(link).toHaveAttribute('href', '/dashboard');
			expect(link).not.toHaveAttribute('target');
			expect(link).not.toHaveAttribute('rel');
		});

		it('renders a React Router Link for nested paths', () => {
			renderLink(<AppLink href="/toolkits/123/edit">Edit</AppLink>);
			const link = screen.getByRole('link', { name: 'Edit' });
			expect(link).toHaveAttribute('href', '/toolkits/123/edit');
		});

		it('renders a React Router Link for root path', () => {
			renderLink(<AppLink href="/">Home</AppLink>);
			const link = screen.getByRole('link', { name: 'Home' });
			expect(link).toHaveAttribute('href', '/');
		});

		it('renders a React Router Link for paths with query params', () => {
			renderLink(<AppLink href="/search?q=test">Search</AppLink>);
			const link = screen.getByRole('link', { name: 'Search' });
			expect(link).toHaveAttribute('href', '/search?q=test');
		});

		it('renders a React Router Link for hash-only hrefs', () => {
			renderLink(<AppLink href="#section">Jump</AppLink>);
			const link = screen.getByRole('link', { name: 'Jump' });
			expect(link.getAttribute('href')).toContain('#section');
		});
	});

	describe('external links (native anchor)', () => {
		it('auto-detects https:// as external', () => {
			renderLink(<AppLink href="https://github.com/jentic">GitHub</AppLink>);
			const link = screen.getByRole('link', { name: 'GitHub' });
			expect(link).toHaveAttribute('href', 'https://github.com/jentic');
			expect(link).toHaveAttribute('target', '_blank');
			expect(link).toHaveAttribute('rel', 'noopener noreferrer');
		});

		it('auto-detects http:// as external', () => {
			renderLink(<AppLink href="http://example.com">Example</AppLink>);
			const link = screen.getByRole('link', { name: 'Example' });
			expect(link).toHaveAttribute('target', '_blank');
		});

		it('auto-detects protocol-relative // as external', () => {
			renderLink(<AppLink href="//cdn.example.com/lib.js">CDN</AppLink>);
			const link = screen.getByRole('link', { name: 'CDN' });
			expect(link).toHaveAttribute('target', '_blank');
			expect(link).toHaveAttribute('rel', 'noopener noreferrer');
		});

		it('auto-detects mailto: as external', () => {
			renderLink(<AppLink href="mailto:hi@jentic.com">Email</AppLink>);
			const link = screen.getByRole('link', { name: 'Email' });
			expect(link).toHaveAttribute('href', 'mailto:hi@jentic.com');
			expect(link).toHaveAttribute('target', '_blank');
		});

		it('auto-detects tel: as external', () => {
			renderLink(<AppLink href="tel:+1234567890">Call</AppLink>);
			const link = screen.getByRole('link', { name: 'Call' });
			expect(link).toHaveAttribute('href', 'tel:+1234567890');
		});

		it('treats ftp:// as external', () => {
			renderLink(<AppLink href="ftp://files.example.com">FTP</AppLink>);
			const link = screen.getByRole('link', { name: 'FTP' });
			expect(link).toHaveAttribute('target', '_blank');
		});
	});

	describe('external prop override', () => {
		it('forces a relative path to render as external when external={true}', () => {
			renderLink(
				<AppLink href="/docs" external>
					API Docs
				</AppLink>,
			);
			const link = screen.getByRole('link', { name: 'API Docs' });
			expect(link).toHaveAttribute('href', '/docs');
			expect(link).toHaveAttribute('target', '_blank');
			expect(link).toHaveAttribute('rel', 'noopener noreferrer');
		});

		it('external={false} does not override auto-detected external URL', () => {
			renderLink(
				<AppLink href="https://github.com" external={false}>
					GH
				</AppLink>,
			);
			const link = screen.getByRole('link', { name: 'GH' });
			expect(link).toHaveAttribute('target', '_blank');
		});
	});

	describe('prop forwarding', () => {
		it('allows overriding target on external links', () => {
			renderLink(
				<AppLink href="https://example.com" target="_self">
					Same tab
				</AppLink>,
			);
			const link = screen.getByRole('link', { name: 'Same tab' });
			expect(link).toHaveAttribute('target', '_self');
		});

		it('allows overriding rel on external links', () => {
			renderLink(
				<AppLink href="https://example.com" rel="nofollow">
					No follow
				</AppLink>,
			);
			const link = screen.getByRole('link', { name: 'No follow' });
			expect(link).toHaveAttribute('rel', 'nofollow');
		});

		it('spreads className to internal links', () => {
			renderLink(
				<AppLink href="/home" className="text-primary">
					Home
				</AppLink>,
			);
			expect(screen.getByRole('link', { name: 'Home' })).toHaveClass('text-primary');
		});

		it('spreads className to external links', () => {
			renderLink(
				<AppLink href="https://example.com" className="text-primary">
					Ext
				</AppLink>,
			);
			expect(screen.getByRole('link', { name: 'Ext' })).toHaveClass('text-primary');
		});

		it('spreads aria attributes', () => {
			renderLink(
				<AppLink href="/settings" aria-label="Go to settings">
					Settings
				</AppLink>,
			);
			expect(screen.getByRole('link', { name: 'Go to settings' })).toBeInTheDocument();
		});

		it('spreads data attributes', () => {
			renderLink(
				<AppLink href="/test" data-testid="my-link">
					Test
				</AppLink>,
			);
			expect(screen.getByTestId('my-link')).toBeInTheDocument();
		});

		it('forwards ref to external links', () => {
			const ref = createRef<HTMLAnchorElement>();
			renderLink(
				<AppLink ref={ref} href="https://example.com">
					Ext
				</AppLink>,
			);
			expect(ref.current).toBeInstanceOf(HTMLAnchorElement);
			expect(ref.current?.href).toContain('example.com');
		});

		it('forwards ref to internal links', () => {
			const ref = createRef<HTMLAnchorElement>();
			renderLink(
				<AppLink ref={ref} href="/home">
					Home
				</AppLink>,
			);
			expect(ref.current).toBeInstanceOf(HTMLAnchorElement);
		});
	});

	describe('accessibility', () => {
		it('internal link has no a11y violations', async () => {
			const { container } = renderLink(<AppLink href="/dashboard">Dashboard</AppLink>);
			const results = await axe.run(container);
			expect(results.violations).toEqual([]);
		});

		it('external link has no a11y violations', async () => {
			const { container } = renderLink(<AppLink href="https://github.com">GitHub</AppLink>);
			const results = await axe.run(container);
			expect(results.violations).toEqual([]);
		});
	});
});
