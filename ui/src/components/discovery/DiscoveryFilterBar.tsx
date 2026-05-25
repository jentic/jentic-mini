import { useSearchParams } from 'react-router-dom';
import type { DiscoverySource } from './DiscoveryCard';
import { SegmentedToggle } from '@/components/ui/SegmentedToggle';
import type { SegmentedToggleOption } from '@/components/ui/SegmentedToggle';

/**
 * Source axis — UI vocabulary.
 *
 *   workspace = entities registered locally in this jentic-mini instance.
 *               (server still calls these `local`; the adapter translates.)
 *   directory = entities available in the upstream public Jentic catalog.
 *               (server still calls these `catalog`.)
 *   'all'     = no filter (both visible).
 */
export type SourceFilter = 'all' | 'workspace' | 'directory';

// ── URL <-> state helpers ─────────────────────────────────────────────────────

function parseSource(raw: string | null): SourceFilter {
	if (!raw) return 'all';
	const parts = raw
		.split(',')
		.map((s) => s.trim())
		.filter(Boolean);
	if (parts.length > 1) return 'all'; // legacy `local,catalog` → all
	const v = parts[0];
	if (v === 'workspace' || v === 'local') return 'workspace';
	if (v === 'directory' || v === 'catalog') return 'directory';
	return 'all';
}

export function matchesSource(
	entitySource: 'workspace' | 'directory',
	filter: SourceFilter,
): boolean {
	return filter === 'all' || filter === entitySource;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Read the raw discovery filter state from the URL. After the May 2026
 * IA simplification only the Source axis remains — Type filtering was
 * removed because the segmented control was teaching users a vocabulary
 * (APIs / Workflows / Endpoints) that didn't carry weight: workspace
 * workflows and operations are already first-class entities listed
 * alongside APIs in search results, and directory workflows ride along
 * with the API row via the `+ workflows` chip.
 */
export function useDiscoveryFilters() {
	const [params] = useSearchParams();
	return {
		source: parseSource(params.get('source')),
	};
}

// ── Segment definitions ───────────────────────────────────────────────────────

const SOURCE_OPTIONS: SegmentedToggleOption<SourceFilter>[] = [
	{ value: 'all', label: 'All' },
	{ value: 'workspace', label: 'My workspace' },
	{ value: 'directory', label: 'Jentic public catalog' },
];

// ── Component ─────────────────────────────────────────────────────────────────

export interface DiscoveryFilterBarProps {
	/**
	 * When `true`, the Source segment (All / My workspace / Jentic public
	 * catalog) is not rendered. Used by pages that hard-code their source
	 * axis (e.g. `/workspace` and `/discover`) — keeping the segment
	 * around would show a non-functional "switch" widget that mutates a
	 * URL param the page deliberately ignores.
	 */
	hideSource?: boolean;
	/**
	 * Optional hint about the page's hard-coded source axis. Reserved for
	 * future per-source segment customisation; kept on the prop surface
	 * so existing callers don't have to change.
	 */
	forcedSource?: DiscoverySource;
	className?: string;
}

/**
 * The Discover surface filter bar. A single Source `SegmentedToggle`
 * wired straight into URL search params so filters are shareable,
 * restorable via back/forward nav, and survive refresh.
 *
 * Designed to live in the sticky toolbar alongside the search input.
 */
export function DiscoveryFilterBar({
	hideSource = false,
	forcedSource: _forcedSource,
	className,
}: DiscoveryFilterBarProps) {
	const [params, setParams] = useSearchParams();
	const source = parseSource(params.get('source'));

	function updateSource(next: SourceFilter) {
		setParams(
			(prev) => {
				const p = new URLSearchParams(prev);
				if (next === 'all') p.delete('source');
				else p.set('source', next);
				return p;
			},
			{ replace: true },
		);
	}

	if (hideSource) {
		// Render nothing rather than an empty container — when the only
		// axis is forced away, there's no filter UI to display.
		return null;
	}

	return (
		<div
			className={className ?? 'flex flex-wrap items-center gap-x-4 gap-y-2'}
			data-testid="discovery-filter-bar"
		>
			<div className="flex items-center gap-2">
				<span className="text-muted-foreground shrink-0 text-[10px] tracking-wider uppercase">
					Source
				</span>
				<SegmentedToggle<SourceFilter>
					layoutId="discovery-source-toggle"
					value={source}
					onChange={updateSource}
					options={SOURCE_OPTIONS}
				/>
			</div>
		</div>
	);
}
