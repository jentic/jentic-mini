import { Loader2, ExternalLink, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { AppLink } from '@/components/ui/AppLink';
import { Button } from '@/components/ui/Button';
import { api } from '@/api/client';

export function InspectPanel({
	capabilityId,
	onClose,
}: {
	capabilityId: string;
	onClose: () => void;
}) {
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

			{params.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-2 font-mono text-xs tracking-wider uppercase">
						Parameters
					</p>
					<div className="space-y-1.5">
						{params.slice(0, 8).map((p: any) => (
							<div key={p.name ?? p.in} className="flex items-baseline gap-2 text-sm">
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

			{auth.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-2 font-mono text-xs tracking-wider uppercase">
						Authentication
					</p>
					<div className="space-y-1">
						{auth.map((a: any) => (
							<div key={a.header ?? a.scheme ?? a.type} className="text-muted-foreground text-sm">
								<span className="text-accent-yellow font-mono text-xs">
									{a.header || a.scheme || a.type}
								</span>
								{a.description && <span className="ml-2">{a.description}</span>}
							</div>
						))}
					</div>
				</div>
			)}

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
