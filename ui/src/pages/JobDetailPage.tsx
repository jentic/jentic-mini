import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Clock, ExternalLink, X } from 'lucide-react';
import { api } from '@/api/client';
import { Badge } from '@/components/ui/Badge';

type StatusVariant = 'success' | 'danger' | 'warning' | 'default';
function statusVariant(s?: string | null): StatusVariant {
	if (s === 'complete') return 'success';
	if (s === 'failed') return 'danger';
	if (s === 'running') return 'warning';
	return 'default';
}

export default function JobDetailPage() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	const { data: job, isLoading } = useQuery({
		queryKey: ['job', id],
		queryFn: () => api.getJob(id!),
		enabled: !!id,
		refetchInterval: (query) => {
			const data = query.state.data;
			if (data && (data.status === 'running' || data.status === 'pending')) return 3000;
			return false;
		},
	});

	const cancelMutation = useMutation({
		mutationFn: () => api.cancelJob(id!),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job', id] }),
	});

	if (isLoading)
		return <div className="text-muted-foreground py-16 text-center">Loading job...</div>;
	if (!job)
		return (
			<div className="text-muted-foreground py-16 text-center">
				<p>Job not found.</p>
				<button
					type="button"
					onClick={() => navigate('/jobs')}
					className="bg-muted border-border mt-4 rounded-lg border px-4 py-2 text-sm"
				>
					Back to Jobs
				</button>
			</div>
		);

	return (
		<div className="max-w-4xl space-y-6">
			<button
				type="button"
				onClick={() => navigate('/jobs')}
				className="text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm transition-colors"
			>
				<ChevronLeft className="h-4 w-4" /> Back to Jobs
			</button>

			<div className="flex items-start justify-between gap-4">
				<div>
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Job Detail
					</p>
					<h1 className="font-heading text-foreground mt-1 font-mono text-xl font-bold break-all">
						{job.id}
					</h1>
				</div>
				{(job.status === 'pending' || job.status === 'running') && (
					<button
						type="button"
						onClick={() => cancelMutation.mutate()}
						disabled={cancelMutation.isPending}
						className="bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors disabled:opacity-50"
					>
						<X className="h-4 w-4" />{' '}
						{cancelMutation.isPending ? 'Cancelling...' : 'Cancel Job'}
					</button>
				)}
			</div>

			{/* Summary */}
			<div className="bg-muted border-border space-y-4 rounded-xl border p-5">
				<h2 className="font-heading text-foreground border-border border-b pb-3 font-semibold">
					Summary
				</h2>
				<div className="grid grid-cols-2 gap-4">
					<div>
						<p className="text-muted-foreground mb-1 text-xs">Status</p>
						<Badge variant={statusVariant(job.status)} className="text-sm">
							{job.status ?? 'unknown'}
						</Badge>
					</div>
					<div>
						<p className="text-muted-foreground mb-1 text-xs">Kind</p>
						<p className="text-foreground font-medium">{job.kind ?? '—'}</p>
					</div>
					{job.toolkit_id && (
						<div>
							<p className="text-muted-foreground mb-1 text-xs">Toolkit</p>
							<code className="text-accent-teal font-mono text-sm">
								{job.toolkit_id}
							</code>
						</div>
					)}
					<div>
						<p className="text-muted-foreground mb-1 text-xs">Created</p>
						<div className="flex items-center gap-1.5">
							<Clock className="text-muted-foreground h-4 w-4" />
							<span className="text-foreground text-sm">
								{job.created_at
									? new Date(job.created_at * 1000).toLocaleString()
									: '—'}
							</span>
						</div>
					</div>
					{job.upstream_job_url && (
						<div className="col-span-2">
							<p className="text-muted-foreground mb-1 text-xs">Upstream Job</p>
							<a
								href={job.upstream_job_url}
								target="_blank"
								rel="noopener noreferrer"
								className="text-primary hover:text-primary/80 flex items-center gap-1 text-sm"
							>
								{job.upstream_job_url}
								<ExternalLink className="h-3 w-3" />
							</a>
						</div>
					)}
				</div>
			</div>

			{job.result && (
				<div className="bg-muted border-border overflow-hidden rounded-xl border">
					<div className="border-border border-b px-5 py-4">
						<h2 className="font-heading text-foreground font-semibold">Result</h2>
					</div>
					<div className="px-5 py-4">
						<pre className="bg-background border-border text-foreground max-h-96 overflow-auto rounded-lg border p-4 font-mono text-xs">
							{typeof job.result === 'string'
								? job.result
								: JSON.stringify(job.result, null, 2)}
						</pre>
					</div>
				</div>
			)}
			{job.error && (
				<div className="bg-muted border-danger/30 overflow-hidden rounded-xl border">
					<div className="border-danger/30 border-b px-5 py-4">
						<h2 className="font-heading text-danger font-semibold">Error</h2>
					</div>
					<div className="px-5 py-4">
						<pre className="bg-danger/10 border-danger/30 text-danger overflow-auto rounded-lg border p-4 font-mono text-xs">
							{job.error}
						</pre>
					</div>
				</div>
			)}
		</div>
	);
}
