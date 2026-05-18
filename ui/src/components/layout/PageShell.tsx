import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

/**
 * Width variants for in-Layout pages. The outer Layout already handles top/bottom
 * chrome padding and horizontal gutters (`p-4 md:p-6`), so PageShell only owns the
 * inner content width cap and vertical rhythm.
 *
 * - `wide` (default): dashboards, lists, tables, anything that wants the screen.
 * - `reading`: detail pages with long prose / sequential sections.
 * - `form`: single-column forms.
 */
type PageWidth = 'wide' | 'reading' | 'form';

const WIDTH_CLASS: Record<PageWidth, string> = {
	wide: 'max-w-screen-2xl',
	reading: 'max-w-4xl',
	form: 'max-w-2xl',
};

export interface PageShellProps {
	children: ReactNode;
	/** Content max-width preset. Defaults to `wide`. */
	width?: PageWidth;
	/** Tailwind class controlling vertical rhythm between top-level children. Defaults to `space-y-6`. */
	spacing?: string;
	/** Extra classes appended to the outer wrapper. */
	className?: string;
}

/**
 * Standard page container for routes mounted under the main `Layout`.
 *
 * ```tsx
 * <PageShell>
 *   <PageHeader title="…" />
 *   …
 * </PageShell>
 * ```
 *
 * Picks a sensible max-width and a consistent vertical rhythm so every page
 * lays out the same way across the app. Auth-only pages (Login, Setup,
 * Approval) intentionally do NOT use this — they render their own centred card.
 */
export function PageShell({
	children,
	width = 'wide',
	spacing = 'space-y-6',
	className,
}: PageShellProps) {
	return (
		<div className={cn('mx-auto w-full', WIDTH_CLASS[width], spacing, className)}>
			{children}
		</div>
	);
}
