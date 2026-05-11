import React, { useState } from 'react';
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
	Loader2,
	Zap,
	Globe,
} from 'lucide-react';
import { AppLink } from '@/components/ui/AppLink';
import { api, apiUrl } from '@/api/client';
import { Badge, MethodBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { Pagination } from '@/components/ui/Pagination';

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
			<Button
				variant="ghost"
				className="hover:bg-background/50 h-auto w-full justify-start px-5 py-4 text-left transition-colors"
				onClick={() => setOpen((o) => !o)}
			>
				<div className="flex w-full items-start gap-3">
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
							<AppLink
								href={`/search?q=${encodeURIComponent(entry.id)}`}
								onClick={(e) => e.stopPropagation()}
								className="text-primary hover:text-primary/80 flex items-center gap-1 text-xs"
							>
								Search ops
							</AppLink>
						)}
						{open ? (
							<ChevronDown className="text-muted-foreground h-4 w-4" />
						) : (
							<ChevronRight className="text-muted-foreground h-4 w-4" />
						)}
					</div>
				</div>
			</Button>
			{open && isLocal && <OperationsPanel apiId={entry.id} />}
			{open && !isLocal && (
				<div className="border-border bg-background/40 text-muted-foreground border-t px-5 py-3 text-sm">
					This API is in the public catalog but not yet imported. Add a credential with
					this API ID to import it automatically.
					<div className="mt-2">
						<AppLink
							href={`/credentials/new?api_id=${encodeURIComponent(entry.id)}`}
							className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-xs"
						>
							<Plus className="h-3 w-3" /> Add credential for {entry.id}
						</AppLink>
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

	if (isLoading) return <LoadingState message="Loading APIs..." />;

	if (isError)
		return (
			<ErrorAlert message="Failed to load registered APIs. Please try refreshing the page." />
		);

	if (apis.length === 0)
		return (
			<EmptyState
				icon={<Database className="h-10 w-10 opacity-30" />}
				title="No APIs registered yet"
				description="Import APIs from the public catalog, or add credentials with an API ID to auto-import them."
				action={
					<AppLink
						href="/credentials/new"
						className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
					>
						<Plus className="h-4 w-4" /> Add Credential
					</AppLink>
				}
			/>
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
				<Pagination
					page={page}
					totalPages={totalPages}
					onPageChange={setPage}
					className="pt-2"
				/>
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
			const catalogRes = await fetch(apiUrl(`/catalog/${apiId}`), { credentials: 'include' });
			if (!catalogRes.ok) {
				const body = await catalogRes.json().catch(() => ({}));
				throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`);
			}
			const catalogEntry = await catalogRes.json();
			if (!catalogEntry.spec_url) {
				throw new Error('No spec URL found for this API in the catalog');
			}

			// Step 2: Import via POST /import
			const importRes = await fetch(apiUrl('/import'), {
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

	if (isLoading) return <LoadingState message="Loading catalog..." />;

	if (error)
		return (
			<div className="space-y-3">
				<ErrorAlert message="Failed to load catalog." />
				<div className="text-center">
					<Button
						variant="ghost"
						size="sm"
						onClick={() => queryClient.invalidateQueries({ queryKey: ['catalog'] })}
					>
						Try again
					</Button>
				</div>
			</div>
		);

	if (isEmpty)
		return (
			<EmptyState
				icon={<Database className="h-10 w-10 opacity-30" />}
				title="Catalog not synced yet"
				description="Pull the manifest from GitHub to browse available APIs."
				action={
					<Button
						onClick={() => refreshMutation.mutate()}
						loading={refreshMutation.isPending}
					>
						<RefreshCw className="h-4 w-4" />
						{refreshMutation.isPending ? 'Syncing catalog...' : 'Sync Catalog'}
					</Button>
				}
			/>
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
							<Button
								variant={filter === f ? 'primary' : 'ghost'}
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
							</Button>
						))}
					</div>
					<Button
						variant="secondary"
						size="sm"
						onClick={() => refreshMutation.mutate()}
						loading={refreshMutation.isPending}
					>
						<RefreshCw className="h-3.5 w-3.5" />
						Refresh
					</Button>
				</div>
			</div>

			{catalogEntries.length === 0 ? (
				<EmptyState
					icon={<Search className="h-8 w-8 opacity-30" />}
					title="No APIs match your filter"
				/>
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
										<AppLink
											href={entry._links.github}
											className="text-muted-foreground hover:text-foreground transition-colors"
										>
											<ExternalLink className="h-4 w-4" />
										</AppLink>
									)}
									{isRegistered ? (
										<AppLink
											href={`/search?q=${encodeURIComponent(entry.api_id)}`}
											className="bg-muted border-border text-foreground hover:bg-muted/60 inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs transition-colors"
										>
											Search ops
										</AppLink>
									) : (
										<Button
											variant="outline"
											size="sm"
											onClick={() => handleImport(entry)}
											loading={importingId === entry.api_id}
										>
											{importingId !== entry.api_id && (
												<Download className="h-3.5 w-3.5" />
											)}
											Import
										</Button>
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
			<PageHeader
				category="Discovery"
				title="API Catalog"
				description="Browse your registered APIs and the Jentic public API catalog."
				actions={
					<AppLink
						href="/credentials/new"
						className="bg-primary text-background hover:bg-primary/80 inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
					>
						<Plus className="h-4 w-4" /> Add Credential
					</AppLink>
				}
			/>

			{/* Tabs + Search */}
			<div className="flex flex-wrap items-center gap-3">
				<div className="bg-muted border-border flex items-center gap-1 rounded-lg border p-0.5">
					{(
						[
							{ key: 'registered', label: 'Your APIs' },
							{ key: 'catalog', label: 'Public Catalog' },
						] as { key: Tab; label: string }[]
					).map((t) => (
						<Button
							variant={tab === t.key ? 'primary' : 'ghost'}
							key={t.key}
							onClick={() => setTab(t.key)}
							className={`rounded px-4 py-1.5 text-sm font-medium transition-colors ${
								tab === t.key
									? 'bg-primary text-background'
									: 'text-muted-foreground hover:text-foreground'
							}`}
						>
							{t.label}
						</Button>
					))}
				</div>
				<div className="min-w-48 flex-1">
					<Input
						type="text"
						value={q}
						onChange={(e) => setQ(e.target.value)}
						placeholder="Filter by name or API ID..."
						aria-label="Filter APIs"
						startIcon={<Search className="h-3.5 w-3.5" />}
						size="sm"
					/>
				</div>
			</div>

			{tab === 'registered' && <RegisteredTab q={q} />}
			{tab === 'catalog' && <CatalogTab q={q} />}
		</div>
	);
}
