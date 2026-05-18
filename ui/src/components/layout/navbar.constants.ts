import {
	Activity,
	Bot,
	Compass,
	Cog,
	FolderOpen,
	KeyRound,
	LayoutDashboard,
	Workflow,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type NavItem = {
	href: string;
	label: string;
	icon: LucideIcon;
	/** Use exact matching (pathname === href) instead of startsWith */
	exact?: boolean;
};

/**
 * Primary navigation items in display order. `NavTabs` measures available
 * width with a `ResizeObserver` and pushes whatever doesn't fit into a
 * "More ▾" dropdown (`BottomNavbar` uses a fixed `TILE_LIMIT` instead).
 *
 * Order is deliberate — frequently-touched routes first, observability and
 * settings last.
 *
 * Icon choices mirror `jentic-webapp` where the concepts overlap
 * (Toolkits → FolderOpen, Workflows → Workflow, Traces → Activity).
 * Mini-only routes (Dashboard, Credentials, Agents, Async Jobs) keep
 * semantically appropriate Lucide icons.
 *
 * Search has been removed as a standalone nav item; it is now the primary
 * interaction on the unified Discover surface (`/catalog`).
 */
export const NAV_ITEMS: NavItem[] = [
	{ href: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
	{ href: '/toolkits', label: 'Toolkits', icon: FolderOpen },
	{ href: '/credentials', label: 'Credentials', icon: KeyRound },
	{ href: '/catalog', label: 'Discover', icon: Compass },
	{ href: '/workflows', label: 'Workflows', icon: Workflow },
	{ href: '/agents', label: 'Agents', icon: Bot },
	{ href: '/traces', label: 'Traces', icon: Activity },
	{ href: '/jobs', label: 'Async Jobs', icon: Cog },
];
