import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, KeyRound, Settings } from 'lucide-react';
import { usePendingRequests } from '@/hooks/usePendingRequests';
import { api } from '@/api/client';

export default function DashboardPage() {
	const { data: pendingRequests } = usePendingRequests();

	const { data: apisPage } = useQuery({
		queryKey: ['apis-count'],
		queryFn: () => api.listApis(1, 1, 'local'),
	});

	const { data: workflows } = useQuery({
		queryKey: ['workflows'],
		queryFn: () => api.listWorkflows(),
	});

	const { data: toolkits } = useQuery({
		queryKey: ['toolkits'],
		queryFn: () => api.listToolkits(),
	});

	const { data: tracesPage } = useQuery({
		queryKey: ['traces-recent'],
		queryFn: () => api.listTraces({ limit: 10 }),
	});

	const traces = (tracesPage as any)?.traces ?? [];

	function timeAgo(ts: number | null | undefined) {
		if (!ts) return '';
		const secs = Math.floor(Date.now() / 1000 - ts);
		if (secs < 60) return `${secs}s ago`;
		if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
		if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
		return `${Math.floor(secs / 86400)}d ago`;
	}

	function statusColor(status: number | null | undefined) {
		if (!status) return 'text-muted-foreground';
		if (status < 300) return 'text-success';
		if (status < 400) return 'text-accent-yellow';
		return 'text-danger';
	}

	return (
		<div className="space-y-6">
			<h1 className="text-foreground text-3xl font-bold">Dashboard</h1>

			{/* CRITICAL: Pending requests alert banner */}
			{pendingRequests && pendingRequests.length > 0 && (
				<div className="bg-warning/10 border-warning/30 w-full rounded-xl border p-4 shadow-md">
					<div className="mb-3 flex items-center gap-3">
						<AlertTriangle className="text-warning h-5 w-5" />
						<h2 className="text-warning text-lg font-bold">Pending Access Requests</h2>
					</div>
					<div className="flex flex-col gap-3">
						{pendingRequests.map((req: any) => (
							<div
								key={req.id}
								className="bg-muted border-border flex items-center justify-between rounded-lg border p-3"
							>
								<div className="flex flex-col gap-1">
									<span className="text-foreground font-semibold">
										{req.toolkit_id}
									</span>
									<span className="text-muted-foreground text-sm">
										{req.type === 'grant' ? (
											<>
												<KeyRound className="-mt-0.5 mr-1 inline h-3.5 w-3.5" />
												Requesting access to credential
											</>
										) : (
											<>
												<Settings className="-mt-0.5 mr-1 inline h-3.5 w-3.5" />
												Requesting permission change
											</>
										)}
										{req.reason && (
											<span className="ml-2 italic">— "{req.reason}"</span>
										)}
									</span>
									<span className="text-muted-foreground text-xs">
										{timeAgo(req.created_at)}
									</span>
								</div>
								{req.approve_url && (
									<Link
										to={req.approve_url.replace(window.location.origin, '')}
										className="bg-warning text-background hover:bg-warning/80 ml-4 shrink-0 rounded-lg px-4 py-2 text-sm font-bold transition-colors"
									>
										Review →
									</Link>
								)}
							</div>
						))}
					</div>
				</div>
			)}

			{/* Stats */}
			<div className="grid grid-cols-2 gap-4 md:grid-cols-4">
				<div className="bg-muted border-border rounded-xl border p-4">
					<div className="text-primary/60 mb-1 font-mono text-xs tracking-wider uppercase">
						APIs Registered
					</div>
					<div className="text-foreground text-3xl font-bold">
						{(apisPage as any)?.total ?? '—'}
					</div>
				</div>
				<div className="bg-muted border-border rounded-xl border p-4">
					<div className="text-primary/60 mb-1 font-mono text-xs tracking-wider uppercase">
						Active Toolkits
					</div>
					<div className="text-foreground text-3xl font-bold">
						{toolkits?.length ?? '—'}
					</div>
				</div>
				<div className="bg-muted border-border rounded-xl border p-4">
					<div className="text-primary/60 mb-1 font-mono text-xs tracking-wider uppercase">
						Workflows
					</div>
					<div className="text-foreground text-3xl font-bold">
						{Array.isArray(workflows) ? workflows.length : '—'}
					</div>
				</div>
				<div className="bg-muted border-border rounded-xl border p-4">
					<div className="text-primary/60 mb-1 font-mono text-xs tracking-wider uppercase">
						Recent Traces
					</div>
					<div className="text-foreground text-3xl font-bold">
						{(tracesPage as any)?.total ?? '—'}
					</div>
				</div>
			</div>

			{/* Quick actions */}
			<div>
				<h2 className="text-muted-foreground mb-3 font-mono text-sm tracking-wider uppercase">
					Quick Actions
				</h2>
				<div className="grid grid-cols-2 gap-3 md:grid-cols-4">
					<Link
						to="/search"
						className="bg-muted border-border text-foreground hover:border-primary hover:text-primary flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
					>
						Search Catalog
					</Link>
					<Link
						to="/credentials"
						className="bg-muted border-border text-foreground hover:border-primary hover:text-primary flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
					>
						Add Credential
					</Link>
					<Link
						to="/toolkits"
						className="bg-muted border-border text-foreground hover:border-primary hover:text-primary flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
					>
						Create Toolkit
					</Link>
					<Link
						to="/catalog"
						className="bg-muted border-border text-foreground hover:border-primary hover:text-primary flex items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors"
					>
						Import an API
					</Link>
				</div>
			</div>

			{/* Recent executions */}
			<div>
				<h2 className="text-muted-foreground mb-3 font-mono text-sm tracking-wider uppercase">
					Recent Executions
				</h2>
				{traces.length === 0 ? (
					<div className="bg-muted border-border text-muted-foreground rounded-xl border p-8 text-center">
						No executions yet. Traces appear here when agents call the broker.
					</div>
				) : (
					<div className="bg-muted border-border overflow-hidden rounded-xl border">
						<table className="w-full text-sm">
							<thead>
								<tr className="border-border text-muted-foreground border-b font-mono text-xs uppercase">
									<th className="px-4 py-3 text-left">Time</th>
									<th className="px-4 py-3 text-left">Toolkit</th>
									<th className="px-4 py-3 text-left">Operation</th>
									<th className="px-4 py-3 text-left">Status</th>
									<th className="px-4 py-3 text-left">Duration</th>
								</tr>
							</thead>
							<tbody>
								{traces.map((t: any) => (
									<tr
										key={t.id}
										className="border-border/50 hover:bg-background/50 border-b transition-colors"
									>
										<td className="text-muted-foreground px-4 py-3 font-mono text-xs">
											{timeAgo(t.created_at)}
										</td>
										<td className="text-foreground px-4 py-3">
											{t.toolkit_id ?? '—'}
										</td>
										<td className="text-muted-foreground max-w-[200px] truncate px-4 py-3 font-mono text-xs">
											{t.operation_id ?? t.workflow_id ?? '—'}
										</td>
										<td
											className={`px-4 py-3 font-mono font-bold ${statusColor(t.http_status)}`}
										>
											{t.http_status ?? t.status}
										</td>
										<td className="text-muted-foreground px-4 py-3">
											{t.duration_ms ? `${t.duration_ms}ms` : '—'}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</div>
		</div>
	);
}
