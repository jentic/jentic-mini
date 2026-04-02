import { Component, useState } from 'react';
import type { ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Workflow, ExternalLink, Zap, AlertTriangle } from 'lucide-react';
import { ArazzoUI } from '@jentic/arazzo-ui';
import { api } from '@/api/client';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { BackButton } from '@/components/ui/BackButton';
import { AppLink } from '@/components/ui/AppLink';
import { LoadingState } from '@/components/ui/LoadingState';
import '@jentic/arazzo-ui/styles.css';

class ArazzoErrorBoundary extends Component<
	{ slug?: string; children: ReactNode },
	{ error: Error | null }
> {
	state = { error: null as Error | null };
	static getDerivedStateFromError(error: Error) {
		return { error };
	}
	componentDidUpdate(prevProps: { slug?: string }) {
		if (prevProps.slug !== this.props.slug && this.state.error) {
			this.setState({ error: null });
		}
	}
	render() {
		if (this.state.error) {
			return (
				<div className="border-border bg-muted rounded-xl border p-8 text-center">
					<AlertTriangle className="text-warning mx-auto mb-3 h-8 w-8" />
					<p className="text-foreground mb-1 text-sm font-medium">
						Workflow visualization failed to render
					</p>
					<p className="text-muted-foreground text-xs">{this.state.error.message}</p>
				</div>
			);
		}
		return this.props.children;
	}
}

function CatalogWorkflowFallback({
	slug,
	navigate,
}: {
	slug: string;
	navigate: (path: string) => void;
}) {
	const queryClient = useQueryClient();
	const [importing, setImporting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const apiId = slug.replace('~', '/');
	const githubUrl = `https://github.com/jentic/jentic-public-apis/tree/main/workflows/${slug}`;
	const encodedSlug = encodeURIComponent(slug);
	const rawArazzoUrl = `https://raw.githubusercontent.com/jentic/jentic-public-apis/refs/heads/main/workflows/${encodedSlug}/workflows.arazzo.json`;
	const arazzoUIUrl = `https://arazzo-ui.jentic.com?document=${encodeURIComponent(rawArazzoUrl)}`;

	const handleImport = async () => {
		setImporting(true);
		setError(null);
		try {
			const catalogRes = await fetch(`/catalog/${apiId}`, { credentials: 'include' });
			if (!catalogRes.ok) {
				const body = await catalogRes.json().catch(() => ({}));
				throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`);
			}
			const catalogEntry = await catalogRes.json();
			if (!catalogEntry.spec_url) {
				throw new Error('No spec URL found for this API in the catalog');
			}
			const importRes = await fetch('/import', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					sources: [{ type: 'url', url: catalogEntry.spec_url, force_api_id: apiId }],
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
			queryClient.invalidateQueries({ queryKey: ['workflows'] });
			navigate('/workflows');
		} catch (e: any) {
			setError(e.message);
		} finally {
			setImporting(false);
		}
	};

	return (
		<div className="max-w-4xl space-y-6">
			<BackButton to="/workflows" label="Back to Workflows" />
			<div className="bg-muted border-border space-y-4 rounded-xl border p-6">
				<div className="flex items-start gap-3">
					<Workflow className="text-accent-pink mt-0.5 h-6 w-6 shrink-0" />
					<div>
						<h1 className="font-heading text-foreground text-xl font-bold">{apiId}</h1>
						<p className="text-muted-foreground mt-0.5 font-mono text-xs">{slug}</p>
					</div>
				</div>
				<p className="text-muted-foreground text-sm">
					This workflow is available in the Jentic public catalog. Import it to view
					details and execute.
				</p>
				{error && <p className="text-danger text-xs">{error}</p>}
				<div className="flex items-center gap-3">
					<Button
						variant="ghost"
						size="sm"
						onClick={handleImport}
						loading={importing}
						className="text-accent-teal hover:text-accent-teal/80"
					>
						<Zap className="h-4 w-4" />
						{importing ? 'Importing...' : 'Import this workflow'}
					</Button>
					<AppLink
						href={githubUrl}
						className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-sm"
					>
						<ExternalLink className="h-3.5 w-3.5" /> View on GitHub
					</AppLink>
					<AppLink
						href={arazzoUIUrl}
						className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-sm"
					>
						<ExternalLink className="h-3.5 w-3.5" /> View using Arazzo UI
					</AppLink>
				</div>
			</div>
		</div>
	);
}

export default function WorkflowDetailPage() {
	const { slug } = useParams<{ slug: string }>();
	const navigate = useNavigate();
	const [view, setView] = useState<'diagram' | 'docs' | 'split'>('docs');

	const {
		data: workflow,
		isLoading,
		error,
	} = useQuery({
		queryKey: ['workflow', slug],
		queryFn: () => api.getWorkflow(slug!),
		enabled: !!slug,
		retry: (failureCount, err: any) => err?.status !== 404 && failureCount < 2,
	});

	const { data: arazzoDoc, isLoading: isLoadingArazzo } = useQuery({
		queryKey: ['workflow-arazzo', slug],
		queryFn: async () => {
			const res = await fetch(`/workflows/${slug}`, {
				headers: { Accept: 'application/vnd.oai.workflows+json' },
				credentials: 'include',
			});
			if (!res.ok) throw new Error('Failed to fetch Arazzo document');
			return res.json();
		},
		enabled: !!slug && !!workflow,
	});

	if (isLoading) return <LoadingState message="Loading workflow..." />;

	const is404 = (error as any)?.status === 404;
	if (error && !is404) {
		return (
			<div className="py-16 text-center">
				<AlertTriangle className="text-danger mx-auto mb-3 h-8 w-8" />
				<p className="text-foreground text-sm font-medium">Failed to load workflow</p>
				<p className="text-muted-foreground mt-1 text-xs">
					{(error as any)?.message || 'Unknown error'}
				</p>
			</div>
		);
	}

	if (!workflow) return <CatalogWorkflowFallback slug={slug!} navigate={navigate} />;

	const steps: any[] = workflow.steps ?? [];
	const involvedApis: string[] = workflow.involved_apis ?? [];
	const showDescription = workflow.description && workflow.description !== workflow.name;

	return (
		<div className="max-w-full space-y-4">
			<BackButton to="/workflows" label="Back to Workflows" />

			<div className="space-y-3">
				<div className="space-y-1">
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Workflow
					</p>
					<div className="flex items-center gap-2">
						<Workflow className="text-accent-pink h-5 w-5 shrink-0" />
						<h1 className="font-heading text-foreground text-xl font-bold">
							{workflow.name ?? workflow.slug}
						</h1>
					</div>
					<p className="text-muted-foreground font-mono text-xs">{workflow.slug}</p>
				</div>

				<div className="flex flex-wrap items-center justify-between gap-4">
					<div className="flex flex-wrap items-center gap-2">
						{steps.length > 0 && (
							<Badge variant="default">
								{steps.length} step{steps.length !== 1 ? 's' : ''}
							</Badge>
						)}
						{involvedApis.map((apiId: string) => (
							<Badge key={apiId} variant="default" className="font-mono text-[10px]">
								{apiId}
							</Badge>
						))}
					</div>

					<div className="bg-muted border-border flex items-center gap-1 rounded-lg border p-0.5">
						{(['diagram', 'split', 'docs'] as const).map((v) => (
							<Button
								key={v}
								variant={view === v ? 'primary' : 'ghost'}
								size="sm"
								onClick={() => setView(v)}
								className="rounded px-3 py-1.5 text-xs"
							>
								{v === 'diagram' ? 'Diagram' : v === 'split' ? 'Split' : 'Docs'}
							</Button>
						))}
					</div>
				</div>

				{showDescription && (
					<p className="text-muted-foreground text-sm">{workflow.description}</p>
				)}
			</div>

			{isLoadingArazzo ? (
				<LoadingState message="Loading workflow visualization..." />
			) : arazzoDoc ? (
				<ArazzoErrorBoundary slug={slug}>
					<div
						className="border-border bg-muted overflow-hidden rounded-xl border"
						style={{ height: '800px' }}
					>
						<ArazzoUI document={arazzoDoc} view={view} onViewChange={setView} />
					</div>
				</ArazzoErrorBoundary>
			) : (
				<div className="text-muted-foreground py-16 text-center">
					Failed to load workflow visualization.
				</div>
			)}
		</div>
	);
}
