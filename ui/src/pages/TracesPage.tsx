import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Activity, ChevronLeft, ChevronRight, Filter, X } from 'lucide-react';
import { api } from '@/api/client';
import type { TraceOut } from '@/api/generated';
import { Badge, StatusBadge } from '@/components/ui/Badge';

function timeAgo(ts?: number | null) {
	if (!ts) return '—';
	const s = Math.floor(Date.now() / 1000 - ts);
	if (s < 60) return 'just now';
	if (s < 3600) return `${Math.floor(s / 60)}m ago`;
	if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
	return `${Math.floor(s / 86400)}d ago`;
}

export default function TracesPage() {
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10));
	const toolkit = searchParams.get('toolkit') || undefined;
	const workflow = searchParams.get('workflow') || undefined;

	const {
		data: tracesPage,
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['traces', page, toolkit, workflow],
		queryFn: () => api.listTraces({ page, limit: 20, toolkit, workflow }),
	});

	const traces = tracesPage?.traces ?? [];
	const total = tracesPage?.total ?? 0;
	const totalPages = Math.ceil(total / 20);

	return (
		<div className="max-w-6xl space-y-5">
			<div>
				<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
					Observability
				</p>
				<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
					Execution Traces
				</h1>
			</div>

			{(toolkit || workflow) && (
				<div className="flex flex-wrap items-center gap-2">
					<Filter className="text-muted-foreground h-4 w-4" />
					{toolkit && (
						<span className="bg-primary/10 text-primary border-primary/20 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs">
							toolkit: {toolkit}
							<button
								type="button"
								aria-label="Clear toolkit filter"
								onClick={() => {
									const p = new URLSearchParams(searchParams);
									p.delete('toolkit');
									setSearchParams(p);
								}}
							>
								<X className="h-3 w-3" />
							</button>
						</span>
					)}
					{workflow && (
						<span className="bg-primary/10 text-primary border-primary/20 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs">
							workflow: {workflow}
							<button
								type="button"
								aria-label="Clear workflow filter"
								onClick={() => {
									const p = new URLSearchParams(searchParams);
									p.delete('workflow');
									setSearchParams(p);
								}}
							>
								<X className="h-3 w-3" />
							</button>
						</span>
					)}
				</div>
			)}

			{isLoading ? (
				<div className="text-muted-foreground py-16 text-center">Loading traces...</div>
			) : isError ? (
				<div className="bg-muted border-border rounded-xl border p-12 text-center">
					<p className="text-danger font-medium">Failed to load traces</p>
					<p className="text-muted-foreground mt-1 text-sm">
						Please try refreshing the page.
					</p>
				</div>
			) : traces.length === 0 ? (
				<div className="bg-muted border-border text-muted-foreground rounded-xl border p-12 text-center">
					<Activity className="mx-auto mb-3 h-10 w-10 opacity-30" />
					<p className="text-foreground font-medium">No traces found</p>
					<p className="mt-1 text-sm">Traces appear here when agents call the broker.</p>
				</div>
			) : (
				<>
					<div className="bg-muted border-border overflow-hidden rounded-xl border">
						<div className="overflow-x-auto">
							<table className="w-full text-sm">
								<thead>
									<tr className="border-border border-b">
										{[
											'Time',
											'Toolkit',
											'Operation / Workflow',
											'Status',
											'Duration',
										].map((h) => (
											<th
												key={h}
												className="text-muted-foreground px-4 py-3 text-left font-mono text-xs tracking-wider uppercase"
											>
												{h}
											</th>
										))}
									</tr>
								</thead>
								<tbody>
									{traces.map((trace: TraceOut) => (
										<tr
											key={trace.id}
											className="border-border/50 hover:bg-background/50 cursor-pointer border-b transition-colors"
											onClick={() => navigate(`/traces/${trace.id}`)}
										>
											<td className="text-muted-foreground px-4 py-3 font-mono text-xs whitespace-nowrap">
												{timeAgo(trace.created_at)}
											</td>
											<td className="text-foreground px-4 py-3">
												{trace.toolkit_id ?? '—'}
											</td>
											<td className="text-muted-foreground max-w-[300px] truncate px-4 py-3 font-mono text-xs">
												{trace.workflow_id && (
													<span className="bg-primary/10 text-primary mr-2 rounded px-1.5 py-0.5 font-mono text-[10px]">
														workflow
													</span>
												)}
												{trace.operation_id ?? trace.workflow_id ?? '—'}
											</td>
											<td className="px-4 py-3">
												{trace.http_status ? (
													<StatusBadge status={trace.http_status} />
												) : (
													<Badge
														variant={
															trace.status === 'error'
																? 'danger'
																: 'success'
														}
													>
														{trace.status ?? '—'}
													</Badge>
												)}
											</td>
											<td className="text-muted-foreground px-4 py-3 text-xs">
												{trace.duration_ms != null
													? `${trace.duration_ms}ms`
													: '—'}
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</div>
					{totalPages > 1 && (
						<div className="flex items-center justify-center gap-3">
							<button
								type="button"
								disabled={page <= 1}
								onClick={() => setPage((p) => p - 1)}
								className="bg-muted border-border hover:bg-muted/60 rounded-lg border px-3 py-1.5 text-sm transition-colors disabled:opacity-40"
							>
								<ChevronLeft className="h-4 w-4" />
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
								<ChevronRight className="h-4 w-4" />
							</button>
						</div>
					)}
				</>
			)}
		</div>
	);
}
