import { ChevronDown, ChevronRight, ChevronUp, Globe, Plus, Workflow, Zap } from 'lucide-react';
import { CatalogPanel } from './CatalogPanel';
import { InspectPanel } from './InspectPanel';
import { OperationsPanel } from './OperationsPanel';
import { AppLink } from '@/components/ui/AppLink';
import { Badge, MethodBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CopyButton } from '@/components/ui/CopyButton';

/**
 * Discriminated entity types that the Discover surface handles.
 *
 * - `operation`  — a single HTTP operation (BM25 result from GET /search).
 * - `api`        — a whole API (from GET /apis or GET /catalog).
 * - `workflow`   — an Arazzo workflow (from GET /workflows).
 */
export type DiscoveryEntityType = 'operation' | 'api' | 'workflow';

/** Source of truth for where the entity lives. */
export type DiscoverySource = 'local' | 'catalog';

/**
 * Minimum required shape for every entity rendered by DiscoveryCard.
 * The `raw` field carries the original server object so each detail
 * panel can reach whatever fields it needs.
 */
export interface DiscoveryEntity {
	id: string;
	type: DiscoveryEntityType;
	source: DiscoverySource;
	/** Human-readable name / title. */
	summary?: string;
	/** Short description. */
	description?: string;
	/** BM25 relevance score (0–1), present on /search results. */
	score?: number;
	/** Parsed HTTP method, only present for `type === 'operation'`. */
	method?: string;
	/** Whether the API has credentials configured (only for `type === 'api'`). */
	hasCredentials?: boolean;
	/** Whether the API is registered locally (only for `type === 'api'`). */
	registered?: boolean;
	/** Step count (only for `type === 'workflow'`). */
	stepsCount?: number;
	/** APIs involved in a workflow. */
	involvedApis?: string[];
	raw: any;
}

function SourcePill({ source }: { source: DiscoverySource }) {
	return (
		<span
			className={`inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] ${
				source === 'local'
					? 'bg-success/10 text-success border-success/20'
					: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
			}`}
		>
			{source === 'local' ? (
				<Zap className="h-2.5 w-2.5" />
			) : (
				<Globe className="h-2.5 w-2.5" />
			)}
			{source}
		</span>
	);
}

function WorkflowCard({
	entity,
	expanded,
	onToggle,
}: {
	entity: DiscoveryEntity;
	expanded: boolean;
	onToggle: () => void;
}) {
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
					<div className="min-w-0 flex-1 space-y-1">
						<div className="flex flex-wrap items-center gap-2">
							<Badge variant="default" className="shrink-0 text-[10px]">
								workflow
							</Badge>
							<SourcePill source={entity.source} />
							{entity.stepsCount != null && entity.stepsCount > 0 && (
								<Badge variant="default" className="text-[10px]">
									{entity.stepsCount} steps
								</Badge>
							)}
						</div>
						<p className="text-foreground text-sm font-medium">
							{entity.summary ?? entity.id}
						</p>
						{entity.description && (
							<p className="text-muted-foreground line-clamp-2 text-xs">
								{entity.description}
							</p>
						)}
						{entity.involvedApis && entity.involvedApis.length > 0 && (
							<div className="flex flex-wrap items-center gap-1">
								{entity.involvedApis.slice(0, 3).map((apiId) => (
									<Badge
										key={apiId}
										variant="default"
										className="font-mono text-[10px]"
									>
										{apiId}
									</Badge>
								))}
								{entity.involvedApis.length > 3 && (
									<span className="text-muted-foreground text-[10px]">
										+{entity.involvedApis.length - 3} more
									</span>
								)}
							</div>
						)}
					</div>
					<div className="flex shrink-0 items-center gap-2">
						<Workflow className="text-accent-pink h-4 w-4 shrink-0" />
						{expanded ? (
							<ChevronDown className="text-muted-foreground h-4 w-4" />
						) : (
							<ChevronRight className="text-muted-foreground h-4 w-4" />
						)}
					</div>
				</div>
			</Button>
			{expanded && (
				<div className="border-border bg-background/40 border-t px-5 py-4">
					<p className="text-muted-foreground text-sm">
						{entity.description ?? 'No further details available.'}
					</p>
					<div className="mt-3">
						<AppLink
							href={`/workflows/${entity.id}`}
							className="text-primary hover:text-primary/80 text-xs"
						>
							Open workflow detail →
						</AppLink>
					</div>
				</div>
			)}
		</div>
	);
}

function ApiCard({
	entity,
	expanded,
	onToggle,
}: {
	entity: DiscoveryEntity;
	expanded: boolean;
	onToggle: () => void;
}) {
	const isLocal = entity.source === 'local';

	return (
		<div
			className={`bg-muted overflow-hidden rounded-xl border transition-all ${expanded ? 'border-primary/40' : 'border-border'}`}
		>
			<Button
				variant="ghost"
				className="hover:bg-background/50 h-auto w-full justify-start px-5 py-4 text-left transition-colors"
				onClick={onToggle}
			>
				<div className="flex w-full items-start gap-3">
					<div className="min-w-0 flex-1 space-y-1">
						<div className="flex flex-wrap items-center gap-2">
							<SourcePill source={entity.source} />
							{entity.hasCredentials && (
								<Badge variant="success" className="text-[10px]">
									credentials
								</Badge>
							)}
						</div>
						<p className="text-foreground font-medium">{entity.summary ?? entity.id}</p>
						{entity.summary && entity.summary !== entity.id && (
							<code className="text-muted-foreground font-mono text-xs">
								{entity.id}
							</code>
						)}
						{entity.description && (
							<p className="text-muted-foreground mt-0.5 line-clamp-1 text-xs">
								{entity.description}
							</p>
						)}
					</div>
					<div className="flex shrink-0 items-center gap-2">
						{isLocal && (
							<button
								type="button"
								onClick={(e) => e.stopPropagation()}
								className="text-primary hover:text-primary/80 flex items-center gap-1 text-xs"
							>
								<AppLink href={`/catalog?q=${encodeURIComponent(entity.id)}`}>
									Search ops
								</AppLink>
							</button>
						)}
						{!isLocal && !entity.registered && (
							<AppLink
								href={`/credentials/new?api_id=${encodeURIComponent(entity.id)}`}
								onClick={(e) => e.stopPropagation()}
								className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
							>
								<Plus className="h-3 w-3" /> Add credential
							</AppLink>
						)}
						{expanded ? (
							<ChevronDown className="text-muted-foreground h-4 w-4" />
						) : (
							<ChevronRight className="text-muted-foreground h-4 w-4" />
						)}
					</div>
				</div>
			</Button>
			{expanded && isLocal && <OperationsPanel apiId={entity.id} />}
			{expanded && !isLocal && <CatalogPanel result={entity.raw} onClose={onToggle} />}
		</div>
	);
}

function OperationCard({
	entity,
	expanded,
	onToggle,
}: {
	entity: DiscoveryEntity;
	expanded: boolean;
	onToggle: () => void;
}) {
	const isLocal = entity.source === 'local';

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
							<Badge
								variant={entity.type === 'workflow' ? 'pending' : 'default'}
								className="shrink-0 text-[10px]"
							>
								{entity.type}
							</Badge>
							<SourcePill source={entity.source} />
							{entity.method && <MethodBadge method={entity.method} />}
						</div>
						<p className="text-foreground text-sm font-medium">
							{entity.summary ?? entity.id}
						</p>
						<div className="flex items-center gap-1.5">
							<code className="text-muted-foreground max-w-xs truncate font-mono text-xs">
								{entity.id}
							</code>
							<CopyButton value={entity.id} />
						</div>
						{entity.description && (
							<p className="text-muted-foreground line-clamp-2 text-xs">
								{entity.description}
							</p>
						)}
					</div>
					<div className="flex shrink-0 items-center gap-2">
						{entity.score != null && (
							<span className="text-muted-foreground font-mono text-[10px]">
								{Math.round(entity.score * 100)}%
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
					<InspectPanel capabilityId={entity.id} onClose={onToggle} />
				) : (
					<CatalogPanel result={entity.raw} onClose={onToggle} />
				))}
		</div>
	);
}

/**
 * Polymorphic discovery row. Renders appropriately for
 * `api`, `workflow`, and `operation` entity types.
 */
export function DiscoveryCard({
	entity,
	expanded,
	onToggle,
}: {
	entity: DiscoveryEntity;
	expanded: boolean;
	onToggle: () => void;
}) {
	if (entity.type === 'workflow') {
		return <WorkflowCard entity={entity} expanded={expanded} onToggle={onToggle} />;
	}
	if (entity.type === 'api') {
		return <ApiCard entity={entity} expanded={expanded} onToggle={onToggle} />;
	}
	return <OperationCard entity={entity} expanded={expanded} onToggle={onToggle} />;
}
