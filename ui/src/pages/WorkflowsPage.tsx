import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Workflow, ChevronRight, Zap, Globe } from 'lucide-react';
import { api } from '@/api/client';
import { Badge } from '@/components/ui/Badge';

export default function WorkflowsPage() {
	const navigate = useNavigate();

	const {
		data: workflows,
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['workflows'],
		queryFn: api.listWorkflows,
	});

	return (
		<div className="max-w-5xl space-y-5">
			<div>
				<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
					Catalog
				</p>
				<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">Workflows</h1>
			</div>

			{isLoading ? (
				<div className="text-muted-foreground py-16 text-center">Loading workflows...</div>
			) : isError ? (
				<div className="bg-muted border-border rounded-xl border p-12 text-center">
					<p className="text-danger font-medium">Failed to load workflows</p>
					<p className="text-muted-foreground mt-1 text-sm">
						Please try refreshing the page.
					</p>
				</div>
			) : !workflows || !Array.isArray(workflows) || workflows.length === 0 ? (
				<div className="text-muted-foreground bg-muted border-border rounded-xl border border-dashed p-12 text-center">
					<Workflow className="mx-auto mb-3 h-10 w-10 opacity-30" />
					<p className="text-foreground font-medium">No workflows registered</p>
					<p className="mt-1 text-sm">Import an Arazzo workflow file to get started.</p>
				</div>
			) : (
				<div className="space-y-2">
					{workflows.map((wf: any) => (
						<div
							key={wf.slug}
							role="button"
							tabIndex={0}
							onClick={() => navigate(`/workflows/${wf.slug}`)}
							onKeyDown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									navigate(`/workflows/${wf.slug}`);
								}
							}}
							className="bg-muted border-border hover:border-primary/40 flex cursor-pointer items-center gap-4 rounded-xl border px-5 py-3.5 transition-colors"
						>
							<div className="min-w-0 flex-1 space-y-1">
								<div className="flex flex-wrap items-center gap-2">
									<Workflow className="text-accent-pink h-3.5 w-3.5 shrink-0" />
									<p className="text-foreground truncate text-sm font-medium">
										{wf.name ?? wf.slug}
									</p>
									<span
										className={`inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] ${
											wf.source === 'local'
												? 'bg-success/10 text-success border-success/20'
												: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
										}`}
									>
										{wf.source === 'local' ? (
											<Zap className="h-2.5 w-2.5" />
										) : (
											<Globe className="h-2.5 w-2.5" />
										)}
										{wf.source === 'local' ? 'local' : 'catalog'}
									</span>
									{wf.steps_count > 0 && (
										<Badge variant="default" className="text-[10px]">
											{wf.steps_count} steps
										</Badge>
									)}
								</div>
								{wf.description && (
									<p className="text-muted-foreground line-clamp-1 text-xs">
										{wf.description}
									</p>
								)}
								{wf.involved_apis && wf.involved_apis.length > 0 && (
									<div className="flex flex-wrap items-center gap-1">
										{wf.involved_apis.slice(0, 3).map((apiId: any) => (
											<Badge
												key={apiId}
												variant="default"
												className="font-mono text-[10px]"
											>
												{apiId}
											</Badge>
										))}
										{wf.involved_apis.length > 3 && (
											<span className="text-muted-foreground text-[10px]">
												+{wf.involved_apis.length - 3} more
											</span>
										)}
									</div>
								)}
							</div>
							<ChevronRight className="text-muted-foreground h-4 w-4 shrink-0" />
						</div>
					))}
				</div>
			)}
		</div>
	);
}
