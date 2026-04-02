import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, X, ChevronDown, ChevronUp, ExternalLink, Loader2, Zap, Globe } from 'lucide-react';
import { api } from '@/api/client';
import { Badge, MethodBadge } from '@/components/ui/Badge';
import { CopyButton } from '@/components/ui/CopyButton';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { AppLink } from '@/components/ui/AppLink';

function parseCapabilityId(id: string) {
	// FORMAT: METHOD/host/path  e.g. GET/api.stripe.com/v1/customers
	const parts = id.split('/');
	if (parts.length >= 2 && /^[A-Z]+$/.test(parts[0])) {
		return { method: parts[0], host: parts[1], path: '/' + parts.slice(2).join('/') };
	}
	return null;
}

function InspectPanel({ capabilityId, onClose }: { capabilityId: string; onClose: () => void }) {
	const {
		data: detail,
		isLoading,
		error,
	} = useQuery({
		queryKey: ['inspect', capabilityId],
		queryFn: () => api.inspectCapability(capabilityId),
		staleTime: 60000,
	});

	if (isLoading)
		return (
			<div className="flex items-center justify-center p-8">
				<Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />
			</div>
		);

	if (error || !detail)
		return (
			<div className="text-danger p-4 text-sm">
				Failed to load details for this capability.
			</div>
		);

	const params: any[] = detail.parameters ?? [];
	const auth: any[] = detail.auth_instructions ?? [];

	return (
		<div className="border-border bg-background/50 space-y-4 border-t p-5">
			<div className="flex items-start justify-between gap-2">
				<div className="space-y-1">
					{detail.api_context?.name && (
						<p className="text-muted-foreground font-mono text-xs">
							{detail.api_context.name}
						</p>
					)}
					{detail.summary && (
						<p className="text-foreground text-sm font-medium">{detail.summary}</p>
					)}
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{detail.description && (
				<p className="text-muted-foreground text-sm leading-relaxed">
					{detail.description}
				</p>
			)}

			{/* Parameters */}
			{params.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-2 font-mono text-xs tracking-wider uppercase">
						Parameters
					</p>
					<div className="space-y-1.5">
						{params.slice(0, 8).map((p: any, i: number) => (
							<div key={i} className="flex items-baseline gap-2 text-sm">
								<code className="text-accent-teal shrink-0 font-mono text-xs">
									{p.name}
								</code>
								{p.required && (
									<span className="text-danger font-mono text-[10px]">
										required
									</span>
								)}
								{p.in && (
									<span className="text-muted-foreground text-[10px]">
										in {p.in}
									</span>
								)}
								{p.description && (
									<span className="text-muted-foreground truncate text-xs">
										{p.description}
									</span>
								)}
							</div>
						))}
						{params.length > 8 && (
							<p className="text-muted-foreground text-xs">
								+ {params.length - 8} more parameters
							</p>
						)}
					</div>
				</div>
			)}

			{/* Auth */}
			{auth.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-2 font-mono text-xs tracking-wider uppercase">
						Authentication
					</p>
					<div className="space-y-1">
						{auth.map((a: any, i: number) => (
							<div key={i} className="text-muted-foreground text-sm">
								<span className="text-accent-yellow font-mono text-xs">
									{a.header || a.scheme || a.type}
								</span>
								{a.description && <span className="ml-2">{a.description}</span>}
							</div>
						))}
					</div>
				</div>
			)}

			{/* Links */}
			<div className="border-border flex items-center gap-3 border-t pt-2">
				{detail._links?.upstream && (
					<AppLink
						href={detail._links.upstream}
						className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-xs"
					>
						<ExternalLink className="h-3 w-3" /> API
					</AppLink>
				)}
				<AppLink
					href={`/traces?capability=${encodeURIComponent(capabilityId)}`}
					className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-xs"
				>
					View traces
				</AppLink>
			</div>
		</div>
	);
}

function CatalogPanel({ result, onClose }: { result: any; onClose: () => void }) {
	const links = result._links ?? {};
	const queryClient = useQueryClient();
	const [importing, setImporting] = useState(false);
	const [imported, setImported] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const apiId = result.api_id ?? result.id;

	const handleImport = async () => {
		setImporting(true);
		setError(null);
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
			setImported(true);
			queryClient.invalidateQueries({ queryKey: ['search'] });
		} catch (e: any) {
			setError(e.message);
		} finally {
			setImporting(false);
		}
	};

	return (
		<div className="border-border bg-background/50 space-y-3 border-t p-5">
			<div className="flex items-start justify-between gap-2">
				<div className="space-y-1">
					<p className="text-foreground text-sm font-medium">{apiId}</p>
					<p className="text-muted-foreground text-xs">
						{imported
							? 'Imported successfully. Search again to see individual operations.'
							: 'This API is available in the Jentic public catalog. Import it to browse and execute its operations.'}
					</p>
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
					<X className="h-4 w-4" />
				</Button>
			</div>
			{error && <p className="text-danger text-xs">{error}</p>}
			<div className="border-border flex items-center gap-3 border-t pt-2">
				{!imported && (
					<Button
						variant="ghost"
						size="sm"
						onClick={handleImport}
						disabled={importing}
						className="text-accent-teal hover:text-accent-teal/80"
					>
						{importing ? (
							<Loader2 className="h-3 w-3 animate-spin" />
						) : (
							<Zap className="h-3 w-3" />
						)}
						{importing ? 'Importing...' : 'Import this API'}
					</Button>
				)}
				{links.github && (
					<AppLink
						href={links.github}
						className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-xs"
					>
						<ExternalLink className="h-3 w-3" /> View on GitHub
					</AppLink>
				)}
			</div>
		</div>
	);
}

function ResultCard({
	result,
	expanded,
	onToggle,
}: {
	result: any;
	expanded: boolean;
	onToggle: () => void;
}) {
	const parsed = parseCapabilityId(result.id ?? '');
	const isLocal = result.source === 'local';

	return (
		<div
			className={`bg-muted overflow-hidden rounded-xl border transition-all ${expanded ? 'border-primary/50' : 'border-border'}`}
		>
			<Button
				variant="ghost"
				className="hover:bg-background/50 h-auto w-full justify-start rounded-none px-5 py-4 text-left transition-colors"
				onClick={onToggle}
			>
				<div className="flex w-full items-start gap-3">
					<div className="min-w-0 flex-1 space-y-1.5">
						<div className="flex flex-wrap items-center gap-2">
							{/* Type */}
							<Badge
								variant={result.type === 'workflow' ? 'pending' : 'default'}
								className="shrink-0 text-[10px]"
							>
								{result.type ?? 'operation'}
							</Badge>
							{/* Source */}
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
							{/* HTTP method badge for operations */}
							{parsed && <MethodBadge method={parsed.method} />}
						</div>

						<div className="flex items-center gap-2">
							<p className="text-foreground text-sm font-medium">
								{result.summary ?? result.id}
							</p>
						</div>

						{/* Capability ID */}
						<div className="flex items-center gap-1.5">
							<code className="text-muted-foreground max-w-xs truncate font-mono text-xs">
								{result.id}
							</code>
							<CopyButton value={result.id ?? ''} />
						</div>

						{result.description && (
							<p className="text-muted-foreground line-clamp-2 text-xs">
								{result.description}
							</p>
						)}
					</div>

					<div className="flex shrink-0 items-center gap-2">
						{result.score != null && (
							<span className="text-muted-foreground font-mono text-[10px]">
								{Math.round(result.score * 100)}%
							</span>
						)}
						{expanded ? (
							<ChevronUp className="text-muted-foreground h-4 w-4" />
						) : (
							<ChevronDown className="text-muted-foreground h-4 w-4" />
						)}
					</div>
				</div>
			</Button>

			{expanded &&
				(isLocal ? (
					<InspectPanel capabilityId={result.id} onClose={onToggle} />
				) : (
					<CatalogPanel result={result} onClose={onToggle} />
				))}
		</div>
	);
}

const EXAMPLE_QUERIES = [
	'send an email',
	'create a Stripe payment',
	'list GitHub pull requests',
	'post a Slack message',
	'get weather forecast',
	'search for documents',
];

export default function SearchPage() {
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const [input, setInput] = useState(searchParams.get('q') ?? '');
	const [query, setQuery] = useState(searchParams.get('q') ?? '');
	const [n, setN] = useState(10);
	const [expandedId, setExpandedId] = useState<string | null>(null);
	const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	// Debounce
	const handleInput = useCallback(
		(value: string) => {
			setInput(value);
			if (debounceRef.current) clearTimeout(debounceRef.current);
			debounceRef.current = setTimeout(() => {
				setQuery(value.trim());
				setN(10);
				setExpandedId(null);
				setSearchParams(value.trim() ? { q: value.trim() } : {}, { replace: true });
			}, 400);
		},
		[setSearchParams],
	);

	useEffect(() => {
		return () => {
			if (debounceRef.current) clearTimeout(debounceRef.current);
		};
	}, []);

	const { data: results, isFetching } = useQuery({
		queryKey: ['search', query, n],
		queryFn: () => api.search(query, n),
		enabled: query.trim().length > 1,
		staleTime: 30000,
		placeholderData: (prev) => prev,
	});

	const hasResults = Array.isArray(results) && results.length > 0;
	const showEmpty = query.trim().length > 1 && !isFetching && !hasResults;

	return (
		<div className="max-w-4xl space-y-6">
			<PageHeader
				category="Discovery"
				title="Search"
				description="Find operations and workflows by natural language intent. BM25 search over your local registry and the Jentic public catalog."
			/>

			{/* Search input */}
			<div className="relative">
				<Input
					autoFocus
					type="text"
					value={input}
					onChange={(e) => handleInput(e.target.value)}
					placeholder='e.g. "send an email" or "create a payment"'
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
						onClick={() => {
							setInput('');
							setQuery('');
							setSearchParams({}, { replace: true });
							setExpandedId(null);
						}}
						className="text-muted-foreground hover:text-foreground absolute inset-y-0 right-4 flex items-center"
					>
						<X className="h-4 w-4" />
					</Button>
				)}
			</div>

			{/* Example queries (shown when empty) */}
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
									setSearchParams({ q }, { replace: true });
								}}
								className="rounded-full"
							>
								{q}
							</Button>
						))}
					</div>
				</div>
			)}

			{/* Results */}
			{hasResults && (
				<div className="space-y-4">
					<div className="flex items-center justify-between">
						<p className="text-muted-foreground text-xs">
							{results.length} result{results.length !== 1 ? 's' : ''} for{' '}
							<span className="text-foreground font-medium">"{query}"</span>
							{isFetching && <span className="text-primary ml-2">Updating...</span>}
						</p>
						<div className="text-muted-foreground flex items-center gap-2 text-xs">
							<span>Show</span>
							{[10, 20, 50].map((val) => (
								<Button
									variant="ghost"
									size="sm"
									key={val}
									onClick={() => setN(val)}
									className={`rounded border px-2 py-0.5 text-xs transition-colors ${n === val ? 'border-primary text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}
								>
									{val}
								</Button>
							))}
						</div>
					</div>

					<div className="space-y-2">
						{results.map((result: any) => (
							<ResultCard
								key={result.id}
								result={result}
								expanded={expandedId === result.id}
								onToggle={() =>
									setExpandedId((prev) => (prev === result.id ? null : result.id))
								}
							/>
						))}
					</div>

					{results.length === n && (
						<div className="pt-2 text-center">
							<Button variant="secondary" onClick={() => setN((prev) => prev + 10)}>
								Load more results
							</Button>
						</div>
					)}
				</div>
			)}

			{/* Empty state */}
			{showEmpty && (
				<EmptyState
					icon={<Search className="h-10 w-10 opacity-30" />}
					title={`No results for "${query}"`}
					description="Try different keywords, or import an API from the Catalog."
					action={
						<Button variant="ghost" onClick={() => navigate('/catalog')}>
							Catalog
						</Button>
					}
				/>
			)}
		</div>
	);
}
