import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Compass, Loader2, Search, X } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { PageHeader } from '@/components/ui/PageHeader';
import { PageShell } from '@/components/layout/PageShell';
import type { DiscoveryEntity } from '@/components/discovery';
import { DiscoveryCard, DiscoveryFilterChips, useDiscoveryFilters } from '@/components/discovery';

const EXAMPLE_QUERIES = [
	'send an email',
	'create a Stripe payment',
	'list GitHub pull requests',
	'post a Slack message',
	'get weather forecast',
	'search for documents',
];

const BROWSE_LIMIT = 50;

// ── Adapters: raw server shapes → DiscoveryEntity ────────────────────────────

function apiToEntity(entry: any): DiscoveryEntity {
	return {
		id: entry.id,
		type: 'api',
		source: entry.source === 'local' ? 'local' : 'catalog',
		summary: entry.name ?? entry.id,
		description: entry.description,
		hasCredentials: Boolean(entry.has_credentials),
		registered: entry.source === 'local',
		raw: entry,
	};
}

function workflowToEntity(wf: any): DiscoveryEntity {
	return {
		id: wf.id ?? wf.slug,
		type: 'workflow',
		source: 'local',
		summary: wf.name ?? wf.id,
		description: wf.description,
		stepsCount: Array.isArray(wf.steps) ? wf.steps.length : undefined,
		involvedApis: wf.api_ids ?? [],
		raw: wf,
	};
}

function searchResultToEntity(r: any): DiscoveryEntity {
	const parsed = parseCapabilityId(r.id ?? '');
	return {
		id: r.id,
		type: r.type === 'workflow' ? 'workflow' : 'operation',
		source: r.source === 'local' ? 'local' : 'catalog',
		summary: r.summary,
		description: r.description,
		score: r.score,
		method: parsed?.method,
		raw: r,
	};
}

function parseCapabilityId(id: string) {
	const parts = id.split('/');
	if (parts.length >= 2 && /^[A-Z]+$/.test(parts[0])) {
		return { method: parts[0], host: parts[1], path: '/' + parts.slice(2).join('/') };
	}
	return null;
}

// ── Browse mode (empty q) ─────────────────────────────────────────────────────

function BrowseResults({
	expandedId,
	onToggle,
}: {
	expandedId: string | null;
	onToggle: (id: string) => void;
}) {
	const { sources, types } = useDiscoveryFilters();

	const wantsLocal = sources.has('local');
	const wantsCatalog = sources.has('catalog');
	const wantsApi = types.has('api');
	const wantsWorkflow = types.has('workflow');

	const { data: localApisPage, isLoading: loadingLocal } = useQuery({
		queryKey: ['apis', 'local', 1, BROWSE_LIMIT],
		queryFn: () => api.listApis(1, BROWSE_LIMIT, 'local'),
		enabled: wantsLocal && wantsApi,
		staleTime: 30000,
	});
	const { data: catalogPage, isLoading: loadingCatalog } = useQuery({
		queryKey: ['catalog', undefined, BROWSE_LIMIT, false, false],
		queryFn: () => api.listCatalog(undefined, BROWSE_LIMIT, false, false),
		enabled: wantsCatalog && wantsApi,
		staleTime: 60000,
	});
	const { data: workflowsRaw, isLoading: loadingWorkflows } = useQuery({
		queryKey: ['workflows'],
		queryFn: () => api.listWorkflows(),
		enabled: wantsWorkflow,
		staleTime: 60000,
	});

	const isLoading = loadingLocal || loadingCatalog || loadingWorkflows;

	// Build merged, deduplicated entity list.
	const entities: DiscoveryEntity[] = [];

	if (wantsApi) {
		const seen = new Set<string>();
		if (wantsLocal) {
			const localApis: any[] = (localApisPage as any)?.data ?? [];
			for (const a of localApis) {
				seen.add(a.id);
				entities.push(apiToEntity(a));
			}
		}
		if (wantsCatalog) {
			const catalogApis: any[] = Array.isArray(catalogPage) ? catalogPage : [];
			for (const a of catalogApis) {
				if (!seen.has(a.id)) entities.push(apiToEntity(a));
			}
		}
	}

	if (wantsWorkflow) {
		const wfs: any[] = Array.isArray(workflowsRaw) ? workflowsRaw : [];
		entities.push(...wfs.map(workflowToEntity));
	}

	if (isLoading) return <LoadingState message="Loading..." />;

	if (entities.length === 0)
		return (
			<EmptyState
				icon={<Compass className="h-10 w-10 opacity-30" />}
				title="Nothing to show"
				description="Try enabling more source or type filters, or import an API."
			/>
		);

	return (
		<div className="space-y-2">
			{entities.map((entity) => (
				<DiscoveryCard
					key={entity.id}
					entity={entity}
					expanded={expandedId === entity.id}
					onToggle={() => onToggle(entity.id)}
				/>
			))}
		</div>
	);
}

// ── Search mode (non-empty q) ─────────────────────────────────────────────────

function SearchResults({
	query,
	n,
	onLoadMore,
	isFetching,
	results,
	expandedId,
	onToggle,
}: {
	query: string;
	n: number;
	onLoadMore: () => void;
	isFetching: boolean;
	results: any[];
	expandedId: string | null;
	onToggle: (id: string) => void;
}) {
	const { sources, types } = useDiscoveryFilters();

	const entities: DiscoveryEntity[] = results
		.map(searchResultToEntity)
		.filter((e) => sources.has(e.source) && types.has(e.type));

	if (entities.length === 0 && !isFetching)
		return (
			<EmptyState
				icon={<Search className="h-10 w-10 opacity-30" />}
				title={`No results for "${query}"`}
				description="Try different keywords or refine the filters above."
			/>
		);

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<p className="text-muted-foreground text-xs">
					{entities.length} result{entities.length !== 1 ? 's' : ''} for{' '}
					<span className="text-foreground font-medium">"{query}"</span>
					{isFetching && <span className="text-primary ml-2">Updating…</span>}
				</p>
				<div className="text-muted-foreground flex items-center gap-2 text-xs">
					<span>Show</span>
					{[10, 20, 50].map((val) => (
						<Button
							key={val}
							variant="ghost"
							size="sm"
							onClick={() => onLoadMore()}
							className={`rounded border px-2 py-0.5 text-xs transition-colors ${n === val ? 'border-primary text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}
						>
							{val}
						</Button>
					))}
				</div>
			</div>

			<div className="space-y-2">
				{entities.map((entity) => (
					<DiscoveryCard
						key={entity.id}
						entity={entity}
						expanded={expandedId === entity.id}
						onToggle={() => onToggle(entity.id)}
					/>
				))}
			</div>

			{results.length === n && (
				<div className="pt-2 text-center">
					<Button variant="secondary" onClick={onLoadMore}>
						Load more results
					</Button>
				</div>
			)}
		</div>
	);
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DiscoverPage() {
	const [searchParams, setSearchParams] = useSearchParams();

	const initialQ = searchParams.get('q') ?? '';
	const [input, setInput] = useState(initialQ);
	const [query, setQuery] = useState(initialQ);
	const [n, setN] = useState(10);
	const [expandedId, setExpandedId] = useState<string | null>(null);
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const isSearchMode = query.trim().length > 1;

	// Sync external URL changes → local state (e.g. back/forward nav).
	useEffect(() => {
		const q = searchParams.get('q') ?? '';
		setInput(q);
		setQuery(q);
	}, [searchParams]);

	const handleInput = useCallback(
		(value: string) => {
			setInput(value);
			if (debounceRef.current) clearTimeout(debounceRef.current);
			debounceRef.current = setTimeout(() => {
				const trimmed = value.trim();
				setQuery(trimmed);
				setN(10);
				setExpandedId(null);
				setSearchParams(
					(prev) => {
						const p = new URLSearchParams(prev);
						if (trimmed) {
							p.set('q', trimmed);
						} else {
							p.delete('q');
						}
						return p;
					},
					{ replace: true },
				);
			}, 400);
		},
		[setSearchParams],
	);

	useEffect(() => {
		return () => {
			if (debounceRef.current) clearTimeout(debounceRef.current);
		};
	}, []);

	const { data: rawResults, isFetching } = useQuery({
		queryKey: ['search', query, n],
		queryFn: () => api.search(query, n),
		enabled: isSearchMode,
		staleTime: 30000,
		placeholderData: (prev) => prev,
	});
	const results: any[] = Array.isArray(rawResults) ? rawResults : [];

	function handleToggle(id: string) {
		setExpandedId((prev) => (prev === id ? null : id));
	}

	function clearSearch() {
		setInput('');
		setQuery('');
		setExpandedId(null);
		setSearchParams(
			(prev) => {
				const p = new URLSearchParams(prev);
				p.delete('q');
				return p;
			},
			{ replace: true },
		);
	}

	return (
		<PageShell>
			<PageHeader
				category="Discovery"
				title="Discover"
				description="Browse your local APIs and workflows, or search by natural language intent."
			/>

			{/* Search input */}
			<div className="relative">
				<Input
					autoFocus
					type="text"
					value={input}
					onChange={(e) => handleInput(e.target.value)}
					placeholder='Search APIs, workflows and operations — e.g. "send an email"'
					aria-label="Search APIs and capabilities"
					startIcon={
						isFetching ? (
							<Loader2 className="h-4 w-4 animate-spin" />
						) : (
							<Search className="h-4 w-4" />
						)
					}
					className="rounded-xl py-3.5 pr-10 pl-11 text-base"
				/>
				{input && (
					<Button
						variant="ghost"
						size="icon"
						onClick={clearSearch}
						className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-4 flex items-center"
					>
						<X className="h-4 w-4" />
					</Button>
				)}
			</div>

			{/* Filter chips */}
			<DiscoveryFilterChips operationDisabled={!isSearchMode} />

			{/* Example queries — shown when no query is entered */}
			{!query && (
				<div className="space-y-3">
					<p className="text-muted-foreground font-mono text-xs tracking-wider uppercase">
						Try searching for
					</p>
					<div className="flex flex-wrap gap-2">
						{EXAMPLE_QUERIES.map((q) => (
							<Button
								variant="secondary"
								size="sm"
								key={q}
								onClick={() => {
									setInput(q);
									setQuery(q);
									setSearchParams(
										(prev) => {
											const p = new URLSearchParams(prev);
											p.set('q', q);
											return p;
										},
										{ replace: true },
									);
								}}
								className="rounded-full"
							>
								{q}
							</Button>
						))}
					</div>
				</div>
			)}

			{/* Main content */}
			{isSearchMode ? (
				<SearchResults
					query={query}
					n={n}
					onLoadMore={() => setN((prev) => prev + 10)}
					isFetching={isFetching}
					results={results}
					expandedId={expandedId}
					onToggle={handleToggle}
				/>
			) : (
				<BrowseResults expandedId={expandedId} onToggle={handleToggle} />
			)}
		</PageShell>
	);
}
