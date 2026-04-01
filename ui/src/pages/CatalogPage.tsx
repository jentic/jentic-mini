import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
	Database,
	RefreshCw,
	Plus,
	ChevronRight,
	ChevronDown,
	ExternalLink,
	Download,
	Search,
	AlertTriangle,
	Loader2,
	Zap,
	Globe,
} from 'lucide-react';
import { api } from '@/api/client';
import { Badge, MethodBadge } from '@/components/ui/Badge';

type Tab = 'registered' | 'catalog';

// ── Registered APIs tab ───────────────────────────────────────────────────────

function OperationsPanel({ apiId }: { apiId: string }) {
	const { data: opsPage, isLoading } = useQuery({
		queryKey: ['ops', apiId],
		queryFn: () => api.listOperations(apiId, 1, 50),
		staleTime: 60000,
	});
	const ops = (opsPage as any)?.data ?? [];
	const total = (opsPage as any)?.total ?? 0;

	if (isLoading)
		return (
			<div className="text-muted-foreground flex items-center gap-2 px-5 py-4 text-sm">
				<Loader2 className="h-4 w-4 animate-spin" /> Loading operations...
			</div>
		);
	if (ops.length === 0)
		return (
			<div className="text-muted-foreground px-5 py-4 text-sm">
				No operations indexed for this API.
			</div>
		);
	return (
		<div className="border-border bg-background/40 border-t">
			<div className="border-border/50 flex items-center justify-between border-b px-5 py-2">
				<span className="text-muted-foreground text-xs">
					{total} operation{total !== 1 ? 's' : ''}
				</span>
			</div>
			<div className="divide-border/50 max-h-72 divide-y overflow-y-auto">
				{ops.map((op: any) => (
					<div
						key={op.id ?? op.operation_id}
						className="flex items-start gap-3 px-5 py-2.5"
					>
						<MethodBadge method={op.method} />
						<div className="min-w-0 flex-1">
							<p className="text-foreground truncate text-sm font-medium">
								{op.summary ?? op.operation_id}
							</p>
							<code className="text-muted-foreground block truncate font-mono text-xs">
								{op.path ?? op.id}
							</code>
						</div>
					</div>
				))}
				{total > 50 && (
					<div className="text-muted-foreground px-5 py-2 text-center text-xs">
						+ {total - 50} more — use Search to find specific operations
					</div>
				)}
			</div>
		</div>
	);
}

function ApiCard({ entry, defaultOpen = false }: { entry: any; defaultOpen?: boolean }) {
	const [open, setOpen] = useState(defaultOpen);
	const isLocal = entry.source === 'local';

	return (
		<div
			className={`bg-muted overflow-hidden rounded-xl border transition-all ${open ? 'border-primary/40' : 'border-border'}`}
		>
			<button
				type="button"
				className="hover:bg-background/50 w-full px-5 py-4 text-left transition-colors"
				onClick={() => setOpen((o) => !o)}
			>
				<div className="flex items-start gap-3">
					<div className="min-w-0 flex-1 space-y-1">
						<div className="flex flex-wrap items-center gap-2">
							<span
								className={`inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] ${
									isLocal
										? 'bg-success/10 text-success border-success/20'
										: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
								}`}
							>
								{isLocal ? (
									<Zap className="h-2.5 w-2.5" />
								) : (
									<Globe className="h-2.5 w-2.5" />
								)}
								{isLocal ? 'local' : 'catalog'}
							</span>
							{entry.has_credentials && (
								<Badge variant="success" className="text-[10px]">
									credentials
								</Badge>
							)}
						</div>
						<p className="text-foreground font-medium">{entry.name ?? entry.id}</p>
						{entry.id !== entry.name && (
							<code className="text-muted-foreground font-mono text-xs">
								{entry.id}
							</code>
						)}
						{entry.description && (
							<p className="text-muted-foreground mt-0.5 line-clamp-1 text-xs">
								{entry.description}
							</p>
						)}
					</div>
					<div className="flex shrink-0 items-center gap-2">
						{isLocal && (
							<Link
								to={`/search?q=${encodeURIComponent(entry.id)}`}
								onClick={(e) => e.stopPropagation()}
								className="text-primary hover:text-primary/80 flex items-center gap-1 text-xs"
							>
								Search ops
							</Link>
						)}
						{open ? (
							<ChevronDown className="text-muted-foreground h-4 w-4" />
						) : (
							<ChevronRight className="text-muted-foreground h-4 w-4" />
						)}
					</div>
				</div>
			</button>
			{open && isLocal && <OperationsPanel apiId={entry.id} />}
			{open && !isLocal && (
				<div className="border-border bg-background/40 text-muted-foreground border-t px-5 py-3 text-sm">
					This API is in the public catalog but not yet imported. Add a credential with
					this API ID to import it automatically.
					<div className="mt-2">
						<Link
							to={`/credentials/new?api_id=${encodeURIComponent(entry.id)}`}
							className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-xs"
						>
							<Plus className="h-3 w-3" /> Add credential for {entry.id}
						</Link>
					</div>
				</div>
			)}
		</div>
	);
}

function RegisteredTab({ q }: { q: string }) {
	const [page, setPage] = useState(1);
	const LIMIT = 20;

	const {
		data: apisPage,
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['apis', 'local', page, q],
		queryFn: () => api.listApis(page, LIMIT, 'local', q || undefined),
		staleTime: 30000,
	});

	const apis: any[] = (apisPage as any)?.data ?? [];
	const total: number = (apisPage as any)?.total ?? 0;
	const totalPages: number = (apisPage as any)?.total_pages ?? 1;

	if (isLoading)
		return <div className="text-muted-foreground py-16 text-center">Loading APIs...</div>;

	if (isError)
		return (
			<div className="bg-muted border-border rounded-xl border p-12 text-center">
				<p className="text-danger font-medium">Failed to load registered APIs</p>
				<p className="text-muted-foreground mt-1 text-sm">
					Please try refreshing the page.
				</p>
			</div>
		);

	if (apis.length === 0)
		return (
			<div className="text-muted-foreground bg-muted border-border rounded-xl border border-dashed p-12 text-center">
				<Database className="mx-auto mb-3 h-10 w-10 opacity-30" />
				<p className="text-foreground font-medium">No APIs registered yet</p>
				<p className="mt-1 mb-4 text-sm">
					Import APIs from the public catalog, or add credentials with an API ID to
					auto-import them.
				</p>
				<Link
					to="/credentials/new"
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
				>
					<Plus className="h-4 w-4" /> Add Credential
				</Link>
			</div>
		);

	return (
		<div className="space-y-4">
			<p className="text-muted-foreground text-xs">
				{total} API{total !== 1 ? 's' : ''} registered
			</p>
			<div className="space-y-2">
				{apis.map((entry: any) => (
					<ApiCard key={entry.id} entry={entry} />
				))}
			</div>
			{totalPages > 1 && (
				<div className="flex items-center justify-center gap-3 pt-2">
					<button
						type="button"
						disabled={page <= 1}
						onClick={() => setPage((p) => p - 1)}
						className="bg-muted border-border hover:bg-muted/60 rounded-lg border px-3 py-1.5 text-sm transition-colors disabled:opacity-40"
					>
						← Prev
					</button>
					<span className="text-muted-foreground text-sm">
						Page {page} of {totalPages}
					</span>
					<button
						type="button"
						disabled={page >= totalPages}
						onClick={() => setPage((p) => p + 1)}
						className="bg-muted border-border hover:bg-muted/60 rounded-lg border px-3 py-1.5 text-sm transition-colors disabled:opacity-40"
					>
						Next →
					</button>
				</div>
			)}
		</div>
	);
}

// ── Public Catalog tab ────────────────────────────────────────────────────────

type CatalogFilter = 'all' | 'registered' | 'unregistered';

function CatalogTab({ q }: { q: string }) {
	const queryClient = useQueryClient();
	const [filter, setFilter] = useState<CatalogFilter>('all');
	const [importingId, setImportingId] = useState<string | null>(null);
	const [importedIds, setImportedIds] = useState<Set<string>>(new Set());

	const {
		data: catalogData,
		isLoading,
		error,
	} = useQuery({
		queryKey: ['catalog', q, filter],
		queryFn: () =>
			api.listCatalog(
				q || undefined,
				100,
				filter === 'registered',
				filter === 'unregistered',
			),
		staleTime: 60000,
	});

	const refreshMutation = useMutation({
		mutationFn: () => api.refreshCatalog(),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['catalog'] });
			queryClient.invalidateQueries({ queryKey: ['apis'] });
		},
	});

	const handleImport = async (entry: any) => {
		const apiId = entry.api_id;
		setImportingId(apiId);
		try {
			// Step 1: Get spec URL from catalog
			const catalogRes = await fetch(`/catalog/${apiId}`, { credentials: 'include' });
			if (!catalogRes.ok) {
				const body = await catalogRes.json().catch(() => ({}));
				throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`);
			}
			const catalogEntry = await catalogRes.json();
			if (!catalogEntry.spec_url) {
				throw new Error('No spec URL found for this API in the catalog');
			}

			// Step 2: Import via POST /import
			const importRes = await fetch('/import', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					sources: [
						{
							type: 'url',
							url: catalogEntry.spec_url,
							force_api_id: apiId,
						},
					],
				}),
			});
			if (!importRes.ok) {
				const body = await importRes.json().catch(() => ({}));
				throw new Error(body.detail || `Import failed (${importRes.status})`);
			}
			const importResult = await importRes.json();
			if (importResult.failed > 0) {
				const err = importResult.results?.[0]?.error || 'Unknown error';
				throw new Error(`Import failed: ${err}`);
			}
			setImportedIds((prev) => new Set(prev).add(apiId));
			queryClient.invalidateQueries({ queryKey: ['catalog'] });
			queryClient.invalidateQueries({ queryKey: ['apis'] });
		} catch (e: any) {
			alert(`Import failed: ${e.message}`);
		} finally {
			setImportingId(null);
		}
	};

	const catalogEntries: any[] = (catalogData as any)?.data ?? [];
	const total: number = (catalogData as any)?.total ?? 0;
	const catalogTotal: number = (catalogData as any)?.catalog_total ?? 0;
	const manifestAge: number | null = (catalogData as any)?.manifest_age_seconds ?? null;
	const isEmpty = (catalogData as any)?.status === 'empty';

	const formatAge = (secs: number) => {
		if (secs < 3600) return `${Math.round(secs / 60)}m ago`;
		if (secs < 86400) return `${Math.round(secs / 3600)}h ago`;
		return `${Math.round(secs / 86400)}d ago`;
	};

	if (isLoading)
		return <div className="text-muted-foreground py-16 text-center">Loading catalog...</div>;

	if (error)
		return (
			<div className="text-muted-foreground p-6 text-center">
				<AlertTriangle className="text-warning mx-auto mb-2 h-8 w-8" />
				<p>Failed to load catalog.</p>
				<button
					type="button"
					onClick={() => queryClient.invalidateQueries({ queryKey: ['catalog'] })}
					className="text-primary mt-3 text-sm hover:underline"
				>
					Try again
				</button>
			</div>
		);

	if (isEmpty)
		return (
			<div className="text-muted-foreground bg-muted border-border space-y-4 rounded-xl border border-dashed p-12 text-center">
				<Database className="mx-auto h-10 w-10 opacity-30" />
				<div>
					<p className="text-foreground font-medium">Catalog not synced yet</p>
					<p className="mt-1 text-sm">
						Pull the manifest from GitHub to browse available APIs.
					</p>
				</div>
				<button
					type="button"
					onClick={() => refreshMutation.mutate()}
					disabled={refreshMutation.isPending}
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
				>
					<RefreshCw
						className={`h-4 w-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`}
					/>
					{refreshMutation.isPending ? 'Syncing catalog...' : 'Sync Catalog'}
				</button>
			</div>
		);

	return (
		<div className="space-y-4">
			{/* Header bar */}
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex items-center gap-2">
					<p className="text-muted-foreground text-xs">
						{total} of {catalogTotal} APIs shown
						{manifestAge != null && (
							<span className="text-muted-foreground/60 ml-2">
								· synced {formatAge(manifestAge)}
							</span>
						)}
					</p>
				</div>
				<div className="flex items-center gap-2">
					{/* Filter */}
					<div className="bg-muted border-border flex items-center gap-1 rounded-lg border p-0.5">
						{(['all', 'registered', 'unregistered'] as CatalogFilter[]).map((f) => (
							<button
								type="button"
								key={f}
								onClick={() => setFilter(f)}
								className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
									filter === f
										? 'bg-primary text-background'
										: 'text-muted-foreground hover:text-foreground'
								}`}
							>
								{f === 'all'
									? 'All'
									: f === 'registered'
										? 'Registered'
										: 'Unregistered'}
							</button>
						))}
					</div>
					<button
						type="button"
						onClick={() => refreshMutation.mutate()}
						disabled={refreshMutation.isPending}
						className="bg-muted border-border text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors disabled:opacity-50"
					>
						<RefreshCw
							className={`h-3.5 w-3.5 ${refreshMutation.isPending ? 'animate-spin' : ''}`}
						/>
						Refresh
					</button>
				</div>
			</div>

			{catalogEntries.length === 0 ? (
				<div className="text-muted-foreground py-12 text-center">
					<p>No APIs match your filter.</p>
				</div>
			) : (
				<div className="space-y-2">
					{catalogEntries.map((entry: any) => {
						const isRegistered = entry.registered || importedIds.has(entry.api_id);
						return (
							<div
								key={entry.api_id}
								className="bg-muted border-border hover:border-border/80 flex items-center gap-4 rounded-xl border px-5 py-3.5 transition-colors"
							>
								<div className="min-w-0 flex-1 space-y-0.5">
									<div className="flex flex-wrap items-center gap-2">
										<p className="text-foreground text-sm font-medium">
											{entry.api_id}
										</p>
										{isRegistered && (
											<Badge variant="success" className="text-[10px]">
												registered
											</Badge>
										)}
									</div>
									{entry.description && (
										<p className="text-muted-foreground truncate text-xs">
											{entry.description}
										</p>
									)}
								</div>
								<div className="flex shrink-0 items-center gap-2">
									{entry._links?.github && (
										<a
											href={entry._links.github}
											target="_blank"
											rel="noopener noreferrer"
											className="text-muted-foreground hover:text-foreground transition-colors"
										>
											<ExternalLink className="h-4 w-4" />
										</a>
									)}
									{isRegistered ? (
										<Link
											to={`/search?q=${encodeURIComponent(entry.api_id)}`}
											className="bg-muted border-border text-foreground hover:bg-muted/60 inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs transition-colors"
										>
											Search ops
										</Link>
									) : (
										<button
											type="button"
											onClick={() => handleImport(entry)}
											disabled={importingId === entry.api_id}
											className="bg-primary/10 border-primary/30 text-primary hover:bg-primary/20 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
										>
											{importingId === entry.api_id ? (
												<Loader2 className="h-3.5 w-3.5 animate-spin" />
											) : (
												<Download className="h-3.5 w-3.5" />
											)}
											Import
										</button>
									)}
								</div>
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CatalogPage() {
	const [tab, setTab] = useState<Tab>('registered');
	const [q, setQ] = useState('');

	return (
		<div className="max-w-5xl space-y-6">
			<div className="flex items-start justify-between gap-4">
				<div>
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Discovery
					</p>
					<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
						API Catalog
					</h1>
					<p className="text-muted-foreground mt-1 text-sm">
						Browse your registered APIs and the Jentic public API catalog.
					</p>
				</div>
				<Link
					to="/credentials/new"
					className="bg-primary text-background hover:bg-primary/80 inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
				>
					<Plus className="h-4 w-4" /> Add Credential
				</Link>
			</div>

			{/* Tabs + Search */}
			<div className="flex flex-wrap items-center gap-3">
				<div className="bg-muted border-border flex items-center gap-1 rounded-lg border p-0.5">
					{(
						[
							{ key: 'registered', label: 'Your APIs' },
							{ key: 'catalog', label: 'Public Catalog' },
						] as { key: Tab; label: string }[]
					).map((t) => (
						<button
							type="button"
							key={t.key}
							onClick={() => setTab(t.key)}
							className={`rounded px-4 py-1.5 text-sm font-medium transition-colors ${
								tab === t.key
									? 'bg-primary text-background'
									: 'text-muted-foreground hover:text-foreground'
							}`}
						>
							{t.label}
						</button>
					))}
				</div>
				<div className="relative min-w-48 flex-1">
					<Search className="text-muted-foreground pointer-events-none absolute inset-y-0 left-3 my-auto h-3.5 w-3.5" />
					<input
						type="text"
						value={q}
						onChange={(e) => setQ(e.target.value)}
						placeholder="Filter by name or API ID..."
						aria-label="Filter APIs"
						className="bg-muted border-border text-foreground placeholder:text-muted-foreground/60 focus:border-primary w-full rounded-lg border py-1.5 pr-3 pl-8 text-sm focus:outline-hidden"
					/>
				</div>
			</div>

			{tab === 'registered' && <RegisteredTab q={q} />}
			{tab === 'catalog' && <CatalogTab q={q} />}
		</div>
	);
}
