import { useState } from 'react';
import { ExternalLink, Loader2, X, Zap } from 'lucide-react';
import { AppLink } from '@/components/ui/AppLink';
import { Button } from '@/components/ui/Button';
import { useImportCatalogApi } from '@/hooks/useImportCatalogApi';

/**
 * Inline expand panel for catalog (non-local) APIs and operations.
 * Uses `useImportCatalogApi` for the two-step import flow so the logic
 * stays in one place.
 */
export function CatalogPanel({ result, onClose }: { result: any; onClose: () => void }) {
	const links = result._links ?? {};
	const apiId = result.api_id ?? result.id;

	const { importApi, isImporting, importedIds, error } = useImportCatalogApi();
	const [localImported, setLocalImported] = useState(false);

	const imported = localImported || importedIds.has(apiId);

	const handleImport = async () => {
		await importApi(apiId);
		setLocalImported(true);
	};

	return (
		<div className="border-border bg-background/50 space-y-3 border-t p-5">
			<div className="flex items-start justify-between gap-2">
				<div className="space-y-1">
					<p className="text-foreground text-sm font-medium">{apiId}</p>
					<p className="text-muted-foreground text-xs">
						{imported
							? 'Imported successfully. Search to see individual operations.'
							: 'This API is available in the Jentic public catalog. Import it to browse and execute its operations.'}
					</p>
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
					<X className="h-4 w-4" />
				</Button>
			</div>
			{error && <p className="text-danger text-xs">{error}</p>}
			<div className="border-border flex items-center gap-3 border-t pt-2">
				{!imported && (
					<Button
						variant="ghost"
						size="sm"
						onClick={handleImport}
						disabled={isImporting}
						className="text-accent-teal hover:text-accent-teal/80"
					>
						{isImporting ? (
							<Loader2 className="h-3 w-3 animate-spin" />
						) : (
							<Zap className="h-3 w-3" />
						)}
						{isImporting ? 'Importing...' : 'Import this API'}
					</Button>
				)}
				{links.github && (
					<AppLink
						href={links.github}
						className="text-primary hover:text-primary/80 inline-flex items-center gap-1 text-xs"
					>
						<ExternalLink className="h-3 w-3" /> View on GitHub
					</AppLink>
				)}
			</div>
		</div>
	);
}
