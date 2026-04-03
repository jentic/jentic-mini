import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import {
	BookOpen,
	ExternalLink,
	Menu,
	X,
	LayoutDashboard,
	Search,
	GitBranch,
	Shield,
	KeyRound,
	Activity,
	Cog,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { JenticLogo } from '@/components/ui/Logo';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { Button } from '@/components/ui/Button';
import { AppLink } from '@/components/ui/AppLink';
import { useAuth } from '@/hooks/useAuth';
import { usePendingRequests } from '@/hooks/usePendingRequests';
import { useUpdateCheck } from '@/hooks/useUpdateCheck';
import { UserService } from '@/api/generated';

function NavLink({
	to,
	icon,
	label,
	exact = false,
	onClick,
}: {
	to: string;
	icon: React.ReactNode;
	label: string;
	exact?: boolean;
	onClick?: () => void;
}) {
	const loc = useLocation();
	const active = exact ? loc.pathname === to : loc.pathname.startsWith(to);
	return (
		<AppLink
			href={to}
			onClick={onClick}
			className={`my-1 flex items-center gap-3 rounded-md px-4 py-2 transition-all duration-150 ${
				active
					? 'bg-muted/80 text-primary border-primary border-l-2'
					: 'text-foreground hover:bg-muted hover:text-primary'
			}`}
		>
			{icon}
			<span className="font-semibold">{label}</span>
		</AppLink>
	);
}

function SidebarContents({ onClose }: { onClose?: () => void }) {
	const { updateAvailable, currentVersion, latestVersion, releaseUrl } = useUpdateCheck();
	return (
		<aside className="bg-muted border-border flex h-full w-60 flex-col border-r">
			<div className="border-border flex h-16 shrink-0 items-center border-b px-6">
				<JenticLogo />
				{onClose && (
					<Button
						variant="ghost"
						size="icon"
						className="ml-auto"
						onClick={onClose}
						aria-label="Close navigation"
					>
						<X className="h-5 w-5" />
					</Button>
				)}
			</div>

			<nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
				<NavLink
					to="/"
					exact
					icon={<LayoutDashboard className="h-4 w-4" />}
					label="Dashboard"
					onClick={onClose}
				/>
				<NavLink
					to="/search"
					icon={<Search className="h-4 w-4" />}
					label="Search"
					onClick={onClose}
				/>

				<div className="text-primary/60 mt-4 mb-2 px-4 font-mono text-[10px] tracking-widest uppercase">
					Directory
				</div>
				<NavLink
					to="/catalog"
					icon={<BookOpen className="h-4 w-4" />}
					label="API Catalog"
					onClick={onClose}
				/>
				<NavLink
					to="/workflows"
					icon={<GitBranch className="h-4 w-4" />}
					label="Workflows"
					onClick={onClose}
				/>

				<div className="text-primary/60 mt-4 mb-2 px-4 font-mono text-[10px] tracking-widest uppercase">
					Security
				</div>
				<NavLink
					to="/toolkits"
					icon={<Shield className="h-4 w-4" />}
					label="Toolkits"
					onClick={onClose}
				/>
				<NavLink
					to="/credentials"
					icon={<KeyRound className="h-4 w-4" />}
					label="Credentials"
					onClick={onClose}
				/>


				<div className="text-primary/60 mt-4 mb-2 px-4 font-mono text-[10px] tracking-widest uppercase">
					Observability
				</div>
				<NavLink
					to="/traces"
					icon={<Activity className="h-4 w-4" />}
					label="Traces"
					onClick={onClose}
				/>
				<NavLink
					to="/jobs"
					icon={<Cog className="h-4 w-4" />}
					label="Async Jobs"
					onClick={onClose}
				/>
			</nav>

			<div className="border-border shrink-0 border-t px-3 py-3">
				{updateAvailable && releaseUrl && (
					<AppLink
						href={releaseUrl}
						className="text-accent-yellow bg-accent-yellow/10 hover:bg-accent-yellow/20 mb-1 flex items-center gap-2 rounded-md px-4 py-2 text-xs font-semibold transition-colors"
					>
						<span className="bg-accent-yellow h-1.5 w-1.5 shrink-0 animate-pulse rounded-full" />
						Update available: {latestVersion}
					</AppLink>
				)}
				<AppLink
					href="/docs"
					external
					className="text-foreground hover:bg-muted hover:text-primary flex items-center gap-3 rounded-md px-4 py-2 text-sm transition-all duration-150"
					aria-label="API (opens in a new tab)"
					title="API (opens in a new tab)"
				>
					<BookOpen className="h-4 w-4" />
					<span className="font-semibold">API</span>
				</AppLink>
				<AppLink
					href="https://jentic.com"
					className="text-muted-foreground/70 hover:text-primary flex items-center gap-1.5 px-4 pt-2 text-[11px] font-medium transition-colors"
				>
					<ExternalLink className="h-3 w-3 shrink-0" />
					More at jentic.com
				</AppLink>
				{currentVersion && (
					<div className="text-muted-foreground/50 px-4 pt-2 font-mono text-[10px]">
						v{currentVersion}
					</div>
				)}
			</div>
		</aside>
	);
}

export function Layout() {
	const [sidebarOpen, setSidebarOpen] = useState(false);
	const { user } = useAuth();
	const { data: pendingRequests } = usePendingRequests();
	const queryClient = useQueryClient();
	const location = useLocation();

	const logoutMutation = useMutation({
		mutationFn: () => UserService.logoutUserLogoutPost(),
		onSuccess: () => {
			queryClient.clear();
			window.location.href = '/login';
		},
	});

	return (
		<div className="bg-background text-foreground flex h-screen overflow-hidden">
			{/* Desktop sidebar — always visible on md+ */}
			<div className="hidden md:flex md:shrink-0">
				<SidebarContents />
			</div>

			{/* Mobile sidebar — slide-over drawer */}
			{sidebarOpen && (
				<>
					{/* Backdrop */}
					<div
						className="fixed inset-0 z-40 bg-black/50 md:hidden"
						onClick={() => setSidebarOpen(false)}
						aria-hidden="true"
					/>
					{/* Drawer */}
					<div className="fixed inset-y-0 left-0 z-50 md:hidden">
						<SidebarContents onClose={() => setSidebarOpen(false)} />
					</div>
				</>
			)}

			{/* Main content */}
			<main className="bg-background/50 flex min-w-0 flex-1 flex-col">
				<header className="border-border bg-background/80 flex h-16 shrink-0 items-center justify-between border-b px-4 backdrop-blur md:px-6">
					<div className="flex items-center gap-3">
						{/* Hamburger — mobile only */}
						<Button
							variant="ghost"
							size="icon"
							className="md:hidden"
							onClick={() => setSidebarOpen(true)}
							aria-label="Open navigation"
						>
							<Menu className="h-5 w-5" />
						</Button>
						{/* Logo in header — mobile only (desktop has it in sidebar) */}
						<div className="md:hidden">
							<JenticLogo />
						</div>
					</div>

					<div className="flex items-center gap-4">
						{pendingRequests && pendingRequests.length > 0 && (
							<AppLink
								href="/toolkits"
								className="bg-danger/10 text-danger border-danger/30 hover:bg-danger/20 flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold transition-colors"
							>
								<span className="bg-danger h-2 w-2 animate-pulse rounded-full" />
								{pendingRequests.length} Pending{' '}
								{pendingRequests.length === 1 ? 'Request' : 'Requests'}
							</AppLink>
						)}
						<div className="text-muted-foreground hidden font-mono text-sm sm:block">
							{user?.username}
						</div>
						<Button
							variant="ghost"
							size="sm"
							onClick={() => logoutMutation.mutate()}
							title="Log out"
						>
							Logout
						</Button>
					</div>
				</header>

				<div className="flex-1 overflow-y-auto p-4 md:p-6">
					<ErrorBoundary resetKey={location.pathname}>
						<Outlet />
					</ErrorBoundary>
				</div>
			</main>
		</div>
	);
}
