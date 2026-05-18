import { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiUrl } from '@/api/client';

export interface ImportResult {
	/** IDs that have been successfully imported in this session. */
	importedIds: Set<string>;
	/** Whether an import is currently in-flight. */
	isImporting: boolean;
	/** Error message from the last failed import, or null. */
	error: string | null;
	/** Trigger the two-step catalog → import flow for an API ID. */
	importApi: (apiId: string) => Promise<void>;
}

/**
 * Encapsulates the two-step API import flow that previously existed as
 * duplicated `handleImport` functions in both `SearchPage` and `CatalogPage`:
 *
 *  1. GET /catalog/:apiId  →  resolve `spec_url`
 *  2. POST /import         →  import the spec into the local registry
 *
 * On success all three query caches are invalidated (`['catalog']`, `['apis']`,
 * `['search']`) so dependent lists refresh automatically.
 */
export function useImportCatalogApi(): ImportResult {
	const queryClient = useQueryClient();
	const [isImporting, setIsImporting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [importedIds, setImportedIds] = useState<Set<string>>(new Set());

	const importApi = useCallback(
		async (apiId: string) => {
			setIsImporting(true);
			setError(null);
			try {
				// Step 1: resolve the spec URL from the catalog entry.
				const catalogRes = await fetch(apiUrl(`/catalog/${apiId}`), {
					credentials: 'include',
				});
				if (!catalogRes.ok) {
					const body = await catalogRes.json().catch(() => ({}));
					throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`);
				}
				const catalogEntry = await catalogRes.json();
				if (!catalogEntry.spec_url) {
					throw new Error('No spec URL found for this API in the catalog');
				}

				// Step 2: import the spec.
				const importRes = await fetch(apiUrl('/import'), {
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

				setImportedIds((prev) => new Set(prev).add(apiId));
				// Invalidate all caches that reflect registration state.
				queryClient.invalidateQueries({ queryKey: ['catalog'] });
				queryClient.invalidateQueries({ queryKey: ['apis'] });
				queryClient.invalidateQueries({ queryKey: ['search'] });
			} catch (e: any) {
				setError(e.message);
			} finally {
				setIsImporting(false);
			}
		},
		[queryClient],
	);

	return { importApi, isImporting, error, importedIds };
}
