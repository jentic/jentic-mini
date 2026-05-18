import { useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';

export type SourceFilter = 'local' | 'catalog';
export type TypeFilter = 'api' | 'workflow' | 'operation';

const SOURCES: SourceFilter[] = ['local', 'catalog'];
const TYPES: TypeFilter[] = ['api', 'workflow', 'operation'];

function Chip({
	label,
	active,
	disabled,
	disabledReason,
	onClick,
}: {
	label: string;
	active: boolean;
	disabled?: boolean;
	disabledReason?: string;
	onClick: () => void;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			disabled={disabled}
			title={disabled ? disabledReason : undefined}
			className={cn(
				'inline-flex items-center rounded-full border px-3 py-1 font-mono text-xs transition-colors',
				'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
				disabled && 'cursor-not-allowed opacity-40',
				!disabled && 'cursor-pointer',
				active
					? 'bg-primary text-primary-foreground border-primary'
					: 'bg-muted text-muted-foreground border-border hover:border-primary/40 hover:text-foreground',
			)}
		>
			{label}
		</button>
	);
}

/**
 * Two chip groups — Source and Type — that read from and write to the
 * current URL search params (`?source=` and `?type=`), so links from
 * outside the page can deep-target a specific slice.
 *
 * `operationDisabled` should be true in browse mode (no /operations
 * list endpoint exists; operations only appear in search results).
 */
export function DiscoveryFilterChips({
	operationDisabled = false,
}: {
	operationDisabled?: boolean;
}) {
	const [params, setParams] = useSearchParams();

	const activeSources = new Set<SourceFilter>(
		(params.get('source') ?? 'local,catalog').split(',').filter(Boolean) as SourceFilter[],
	);
	const activeTypes = new Set<TypeFilter>(
		(params.get('type') ?? 'api,workflow,operation').split(',').filter(Boolean) as TypeFilter[],
	);

	function toggleSource(src: SourceFilter) {
		const next = new Set(activeSources);
		if (next.has(src)) {
			if (next.size === 1) return; // keep at least one active
			next.delete(src);
		} else {
			next.add(src);
		}
		setParams((prev) => {
			const p = new URLSearchParams(prev);
			p.set('source', [...next].join(','));
			return p;
		});
	}

	function toggleType(tp: TypeFilter) {
		const next = new Set(activeTypes);
		if (next.has(tp)) {
			if (next.size === 1) return; // keep at least one active
			next.delete(tp);
		} else {
			next.add(tp);
		}
		setParams((prev) => {
			const p = new URLSearchParams(prev);
			p.set('type', [...next].join(','));
			return p;
		});
	}

	return (
		<div className="flex flex-wrap items-center gap-3">
			<div className="flex items-center gap-1.5">
				<span className="text-muted-foreground shrink-0 text-[10px] tracking-wider uppercase">
					Source
				</span>
				{SOURCES.map((src) => (
					<Chip
						key={src}
						label={src}
						active={activeSources.has(src)}
						onClick={() => toggleSource(src)}
					/>
				))}
			</div>
			<span className="bg-border h-4 w-px" aria-hidden="true" />
			<div className="flex items-center gap-1.5">
				<span className="text-muted-foreground shrink-0 text-[10px] tracking-wider uppercase">
					Type
				</span>
				{TYPES.map((tp) => (
					<Chip
						key={tp}
						label={tp}
						active={activeTypes.has(tp)}
						disabled={tp === 'operation' && operationDisabled}
						disabledReason="Operations only appear in search results — enter a query above"
						onClick={() => !operationDisabled && toggleType(tp)}
					/>
				))}
			</div>
		</div>
	);
}

/** Read the current chip state from the URL (for use inside DiscoverPage). */
export function useDiscoveryFilters() {
	const [params] = useSearchParams();

	const sources = new Set<SourceFilter>(
		(params.get('source') ?? 'local,catalog').split(',').filter(Boolean) as SourceFilter[],
	);
	const types = new Set<TypeFilter>(
		(params.get('type') ?? 'api,workflow,operation').split(',').filter(Boolean) as TypeFilter[],
	);

	return { sources, types };
}
