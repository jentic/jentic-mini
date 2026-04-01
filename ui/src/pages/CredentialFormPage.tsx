import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, AlertTriangle, Search, Check, ChevronRight, Loader2 } from 'lucide-react';
import { api } from '@/api/client';
import type { CredentialCreate, CredentialPatch, ApiOut } from '@/api/types';

// ── Helpers ────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, ms: number): T {
	const [debounced, setDebounced] = useState(value);
	useEffect(() => {
		const t = setTimeout(() => setDebounced(value), ms);
		return () => clearTimeout(t);
	}, [value, ms]);
	return debounced;
}

type SchemeType = 'bearer' | 'basic' | 'apiKey' | 'oauth2' | 'unknown';

type RawSchemes = Record<string, { type?: string; scheme?: string }> | null | undefined;

interface SchemeOption {
	name: string; // key from securitySchemes (e.g. "bearerAuth")
	type: SchemeType;
	label: string; // human label (e.g. "Bearer Token")
}

const SCHEME_TYPE_PRIORITY: SchemeType[] = ['bearer', 'apiKey', 'basic', 'oauth2', 'unknown'];
const SCHEME_TYPE_LABELS: Record<SchemeType, string> = {
	bearer: 'Bearer Token',
	apiKey: 'API Key',
	basic: 'Basic Auth',
	oauth2: 'OAuth 2.0',
	unknown: 'Credential',
};

function schemeTypeFromRaw(s: { type?: string; scheme?: string }): SchemeType {
	if (s.type === 'oauth2') return 'oauth2';
	if (s.type === 'http' && s.scheme?.toLowerCase() === 'bearer') return 'bearer';
	if (s.type === 'http' && s.scheme?.toLowerCase() === 'basic') return 'basic';
	if (s.type === 'apiKey') return 'apiKey';
	return 'unknown';
}

/** Returns all scheme options from a spec, sorted by priority. */
function parseSchemeOptions(schemes: RawSchemes): SchemeOption[] {
	if (!schemes || Object.keys(schemes).length === 0) return [];
	const options: SchemeOption[] = Object.entries(schemes).map(([name, s]) => {
		const type = schemeTypeFromRaw(s);
		return { name, type, label: SCHEME_TYPE_LABELS[type] };
	});
	// Sort by priority, dedup labels (keep first of each type)
	const seen = new Set<SchemeType>();
	return options
		.sort((a, b) => SCHEME_TYPE_PRIORITY.indexOf(a.type) - SCHEME_TYPE_PRIORITY.indexOf(b.type))
		.filter((o) => {
			if (seen.has(o.type)) return false;
			seen.add(o.type);
			return true;
		});
}

function inferSchemeTypeFromSchemes(schemes: RawSchemes): SchemeType {
	const options = parseSchemeOptions(schemes);
	return options[0]?.type ?? 'unknown';
}

function firstSchemeNameFromSchemes(schemes: RawSchemes): string | null {
	if (!schemes) return null;
	return Object.keys(schemes)[0] ?? null;
}

/** Fetch security schemes for a selected API.
 *  - local API: use already-fetched detail (has security_schemes)
 *  - catalog API: fetch catalog entry → get spec_url → fetch spec → parse securitySchemes
 *  Returns { schemes, loading }
 */
function useApiSchemes(selectedApi: ApiOut | null): { schemes: RawSchemes; loading: boolean } {
	const isCatalog = selectedApi?.source === 'catalog';
	const isLocal = selectedApi?.source === 'local' || (!!selectedApi && !selectedApi.source);

	// Local: fetch full API detail
	const { data: localDetail, isLoading: localLoading } = useQuery({
		queryKey: ['api-detail', selectedApi?.id],
		queryFn: () => api.getApi(selectedApi!.id),
		enabled: !!selectedApi && isLocal,
	});

	// Catalog step 1: get catalog entry to find spec_url
	const { data: catalogEntry, isLoading: entryLoading } = useQuery({
		queryKey: ['catalog-entry', selectedApi?.id],
		queryFn: () => api.getCatalogEntry(selectedApi!.id),
		enabled: !!selectedApi && isCatalog,
	});

	const specUrl: string | null = (catalogEntry as any)?.spec_url ?? null;

	// Catalog step 2: fetch the raw spec from GitHub (public, no auth)
	const { data: spec, isLoading: specLoading } = useQuery({
		queryKey: ['spec', specUrl],
		queryFn: async () => {
			const res = await fetch(specUrl!);
			if (!res.ok) throw new Error(`Failed to fetch spec: ${res.status}`);
			return res.json();
		},
		enabled: !!specUrl,
		staleTime: 5 * 60 * 1000, // cache for 5 min
	});

	if (isLocal) {
		const schemes = (localDetail as any)?.security_schemes as RawSchemes;
		return { schemes, loading: localLoading };
	}

	if (isCatalog) {
		const schemes = (spec as any)?.components?.securitySchemes as RawSchemes;
		return { schemes, loading: entryLoading || specLoading };
	}

	return { schemes: null, loading: false };
}

// ── Step 1 — API Picker ────────────────────────────────────────────────────

function ApiPicker({ onSelect }: { onSelect: (api: ApiOut) => void }) {
	const [query, setQuery] = useState('');
	const debouncedQuery = useDebounce(query, 250);
	const inputRef = useRef<HTMLInputElement>(null);

	useEffect(() => {
		inputRef.current?.focus();
	}, []);

	const { data, isLoading } = useQuery({
		queryKey: ['apis-search', debouncedQuery],
		queryFn: () => api.listApis(1, 30, undefined, debouncedQuery),
		enabled: debouncedQuery.length > 0,
		placeholderData: (prev) => prev,
	});

	const items = (data?.items ?? (data as any)?.data ?? []) as ApiOut[];
	const local = items.filter((a: ApiOut) => a.source === 'local');
	const catalog = items.filter((a: ApiOut) => a.source === 'catalog');

	return (
		<div className="space-y-3">
			<div className="relative">
				<Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
				<input
					ref={inputRef}
					type="text"
					value={query}
					onChange={(e) => setQuery(e.target.value)}
					placeholder="Search APIs (GitHub, Gmail, Stripe…)"
					aria-label="Search APIs"
					className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border py-2.5 pr-3 pl-9 focus:outline-hidden"
				/>
				{isLoading && (
					<Loader2 className="text-muted-foreground absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 animate-spin" />
				)}
			</div>

			{items.length === 0 && !isLoading && debouncedQuery && (
				<p className="text-muted-foreground py-4 text-center text-sm">
					No APIs found for "{debouncedQuery}"
				</p>
			)}

			{local.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-1.5 px-1 font-mono text-[10px] tracking-widest uppercase">
						Available locally
					</p>
					<div className="space-y-1">
						{local.map((a: ApiOut) => (
							<ApiRow key={a.id} api={a} onSelect={onSelect} />
						))}
					</div>
				</div>
			)}

			{catalog.length > 0 && (
				<div>
					<p className="text-muted-foreground mb-1.5 px-1 font-mono text-[10px] tracking-widest uppercase">
						From public catalog
					</p>
					<div className="space-y-1">
						{catalog.map((a: ApiOut) => (
							<ApiRow key={a.id} api={a} onSelect={onSelect} />
						))}
					</div>
				</div>
			)}

			{!debouncedQuery && items.length === 0 && !isLoading && (
				<p className="text-muted-foreground py-6 text-center text-sm">
					Start typing to search 10,000+ APIs
				</p>
			)}
		</div>
	);
}

function ApiRow({ api: a, onSelect }: { api: ApiOut; onSelect: (api: ApiOut) => void }) {
	const hasCreds = !!a.has_credentials;
	return (
		<button
			type="button"
			onClick={() => onSelect(a)}
			className="bg-background hover:bg-muted/60 border-border group flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors"
		>
			<div className="min-w-0">
				<div className="flex items-center gap-2">
					<span className="text-foreground truncate text-sm font-medium">
						{a.name ?? a.id}
					</span>
					{hasCreds && (
						<span className="bg-success/15 text-success border-success/30 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px]">
							configured
						</span>
					)}
				</div>
				{a.description && (
					<p className="text-muted-foreground mt-0.5 truncate text-xs">
						{a.description as string}
					</p>
				)}
			</div>
			<ChevronRight className="text-muted-foreground group-hover:text-foreground h-4 w-4 shrink-0 transition-colors" />
		</button>
	);
}

// ── Step 2 — Credential Fields ─────────────────────────────────────────────

interface CredFieldsProps {
	selectedApi: ApiOut;
	onBack: () => void;
	onSaved: () => void;
	editId?: string;
	existing?: any;
}

function CredentialFields({ selectedApi, onBack, onSaved, editId, existing }: CredFieldsProps) {
	const queryClient = useQueryClient();
	const isEdit = !!editId;

	// Fetch security schemes from spec (local: API detail, catalog: raw spec via GitHub)
	const { schemes, loading: schemesLoading } = useApiSchemes(selectedApi);
	const schemeOptions = parseSchemeOptions(schemes);
	const defaultScheme = schemeOptions[0] ?? null;
	const [selectedScheme, setSelectedScheme] = useState<SchemeOption | null>(null);

	// Reset scheme selection and fields when API changes
	useEffect(() => {
		setSelectedScheme(null);
		setLabel(selectedApi.name ?? selectedApi.id);
		setValue('');
		setIdentity('');
		setError(null);
	}, [selectedApi.id]);

	// Prefill from existing credential in edit mode
	useEffect(() => {
		if (existing) {
			setLabel(existing.label ?? '');
			setIdentity(existing.identity ?? '');
			// value is write-only — leave blank
		}
	}, [existing]);

	const activeScheme = selectedScheme ?? defaultScheme;
	const schemeType = activeScheme?.type ?? 'unknown';
	const schemeName = activeScheme?.name ?? firstSchemeNameFromSchemes(schemes);

	const [label, setLabel] = useState(existing?.label ?? selectedApi.name ?? selectedApi.id);
	const [value, setValue] = useState('');
	const [identity, setIdentity] = useState(existing?.identity ?? '');
	const [error, setError] = useState<string | null>(null);

	// For OAuth, show a different CTA
	const hasOAuthBroker = !!(selectedApi.oauth_broker_id as string | undefined);

	const createMutation = useMutation({
		mutationFn: (d: CredentialCreate) => api.createCredential(d),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['credentials'] });
			onSaved();
		},
		onError: (e: Error) => setError(e.message),
	});

	const updateMutation = useMutation({
		mutationFn: (d: CredentialPatch) => api.updateCredential(editId!, d),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['credentials'] });
			onSaved();
		},
		onError: (e: Error) => setError(e.message),
	});

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (schemeType === 'oauth2') return;
		setError(null);

		// Derive auth_type from scheme
		const authTypeMap: Record<SchemeType, CredentialCreate['auth_type']> = {
			bearer: 'bearer',
			apiKey: 'apiKey',
			basic: 'basic',
			oauth2: undefined,
			unknown: undefined,
		};

		if (isEdit) {
			updateMutation.mutate({
				label: label || null,
				api_id: selectedApi.id,
				auth_type: authTypeMap[schemeType],
				value: value || null,
				identity: identity || null,
			});
		} else {
			if (!value) {
				setError('Credential value is required');
				return;
			}
			createMutation.mutate({
				label,
				api_id: selectedApi.id,
				auth_type: authTypeMap[schemeType],
				value,
				identity: identity || undefined,
			});
		}
	};

	const isLoading = createMutation.isPending || updateMutation.isPending;

	if (schemesLoading) {
		return (
			<div className="text-muted-foreground flex items-center justify-center gap-2 py-10">
				<Loader2 className="h-5 w-5 animate-spin" />
				<span className="text-sm">Reading API spec…</span>
			</div>
		);
	}

	return (
		<form onSubmit={handleSubmit} className="space-y-5">
			{/* Selected API summary */}
			<div className="bg-muted/50 border-border flex items-center gap-2 rounded-lg border px-3 py-2.5">
				<div className="min-w-0 flex-1">
					<p className="text-foreground text-sm font-medium">
						{selectedApi.name ?? selectedApi.id}
					</p>
					<p className="text-muted-foreground truncate font-mono text-xs">
						{selectedApi.id}
					</p>
				</div>
				<button
					type="button"
					onClick={onBack}
					className="text-muted-foreground hover:text-foreground shrink-0 text-xs transition-colors"
				>
					Change
				</button>
			</div>

			{/* Scheme picker — only shown when multiple auth types available */}
			{schemeOptions.length > 1 && (
				<fieldset>
					<legend className="text-muted-foreground mb-1.5 block text-xs">
						Auth method
					</legend>
					<div className="flex flex-wrap gap-1.5">
						{schemeOptions.map((opt) => (
							<button
								key={opt.name}
								type="button"
								onClick={() => setSelectedScheme(opt)}
								className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
									activeScheme?.name === opt.name
										? 'bg-primary text-background border-primary font-medium'
										: 'bg-background text-muted-foreground border-border hover:text-foreground'
								}`}
							>
								{opt.label}
							</button>
						))}
					</div>
				</fieldset>
			)}

			{/* Label */}
			<div>
				<label htmlFor="cred-label" className="text-muted-foreground mb-1 block text-xs">
					Label
				</label>
				<input
					id="cred-label"
					type="text"
					value={label}
					onChange={(e) => setLabel(e.target.value)}
					required
					className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
				/>
			</div>

			{/* OAuth flow */}
			{schemeType === 'oauth2' &&
				(() => {
					const apiName = selectedApi.name ?? selectedApi.id;
					const prompt = `Please set up OAuth access for ${apiName} (api_id: "${selectedApi.id}") on my Jentic Mini instance at ${window.location.host}, so I can use it in my workflows.`;
					return (
						<div className="bg-muted/50 border-border space-y-3 rounded-lg border p-4">
							<p className="text-foreground text-sm font-medium">OAuth required</p>
							<p className="text-muted-foreground text-xs">
								{apiName} uses OAuth 2.0. Ask your agent to set this up — copy the
								prompt below and send it:
							</p>
							<div className="relative">
								<pre className="bg-background border-border text-foreground rounded border p-3 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">
									{prompt}
								</pre>
								<button
									type="button"
									onClick={() => navigator.clipboard.writeText(prompt)}
									className="bg-muted border-border text-muted-foreground hover:text-foreground absolute top-2 right-2 rounded border px-2 py-0.5 text-[10px] transition-colors"
								>
									Copy
								</button>
							</div>
							{hasOAuthBroker && (
								<a
									href="/oauth-brokers"
									className="text-primary inline-block text-xs hover:underline"
								>
									OAuth broker already configured — connect here →
								</a>
							)}
						</div>
					);
				})()}

			{/* Basic auth: username + password */}
			{schemeType === 'basic' && (
				<>
					<div>
						<label
							htmlFor="cred-username"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Username
						</label>
						<input
							id="cred-username"
							type="text"
							value={identity}
							onChange={(e) => setIdentity(e.target.value)}
							placeholder="Your username"
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
						/>
					</div>
					<div>
						<label
							htmlFor="cred-password"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Password {!isEdit && '*'}
						</label>
						<input
							id="cred-password"
							type="password"
							value={value}
							onChange={(e) => setValue(e.target.value)}
							required={!isEdit}
							placeholder={isEdit ? 'Leave blank to keep existing' : 'Your password'}
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
						/>
					</div>
				</>
			)}

			{/* Bearer / apiKey / unknown: single token field */}
			{(schemeType === 'bearer' || schemeType === 'apiKey' || schemeType === 'unknown') && (
				<div>
					<label
						htmlFor="cred-token"
						className="text-muted-foreground mb-1 block text-xs"
					>
						{schemeType === 'bearer'
							? 'Bearer Token'
							: schemeType === 'apiKey'
								? 'API Key'
								: 'Credential Value'}
						{!isEdit && ' *'}
						{isEdit && (
							<span className="text-muted-foreground/60">
								{' '}
								(leave blank to keep existing)
							</span>
						)}
					</label>
					<textarea
						id="cred-token"
						value={value}
						onChange={(e) => setValue(e.target.value)}
						rows={3}
						required={!isEdit}
						placeholder="Paste your token or API key…"
						className="bg-background border-border text-foreground focus:border-primary w-full resize-none rounded-lg border px-3 py-2 font-mono text-sm focus:outline-hidden"
					/>
					<p className="text-muted-foreground mt-1 text-xs">
						<AlertTriangle className="-mt-0.5 inline h-3 w-3" /> Stored encrypted. Never
						shown again after saving.
					</p>
				</div>
			)}

			{error && (
				<div
					role="alert"
					className="text-danger bg-danger/10 border-danger/30 flex items-center gap-2 rounded-lg border p-3 text-sm"
				>
					<AlertTriangle className="h-4 w-4 shrink-0" />
					{error}
				</div>
			)}

			{schemeType !== 'oauth2' && (
				<div className="flex gap-2 pt-2">
					<button
						type="submit"
						disabled={isLoading}
						className="bg-primary text-background hover:bg-primary/80 flex-1 rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50"
					>
						{isLoading ? 'Saving…' : isEdit ? 'Update Credential' : 'Save Credential'}
					</button>
					<button
						type="button"
						onClick={onBack}
						className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-4 py-2 transition-colors"
					>
						Cancel
					</button>
				</div>
			)}
		</form>
	);
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function CredentialFormPage() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const isEdit = !!id;

	const [selectedApi, setSelectedApi] = useState<ApiOut | null>(null);
	const [step, setStep] = useState<'pick' | 'fill'>(isEdit ? 'fill' : 'pick');

	// For edit mode, load the existing credential to pre-select its API
	const { data: existing } = useQuery({
		queryKey: ['credential', id],
		queryFn: () => api.getCredential(id!),
		enabled: isEdit,
	});

	// When editing, fetch the API for the existing credential
	const { data: existingApi } = useQuery({
		queryKey: ['api', existing?.api_id],
		queryFn: () => api.getApi(existing!.api_id!),
		enabled: isEdit && !!existing?.api_id,
	});

	useEffect(() => {
		if (existingApi) {
			setSelectedApi(existingApi as ApiOut);
			setStep('fill');
		} else if (isEdit && existing && !existing.api_id) {
			// No api_id — fall back to picker
			setStep('pick');
		}
	}, [existingApi, existing, isEdit]);

	const handleApiSelect = (a: ApiOut) => {
		setSelectedApi(a);
		setStep('fill');
	};

	return (
		<div className="max-w-2xl space-y-6">
			<button
				type="button"
				onClick={() => navigate('/credentials')}
				className="text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm transition-colors"
			>
				<ChevronLeft className="h-4 w-4" /> Back to Credentials
			</button>

			<div>
				<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
					Management
				</p>
				<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
					{isEdit ? 'Edit Credential' : 'Add Credential'}
				</h1>
			</div>

			{/* Step indicator */}
			{!isEdit && (
				<div className="text-muted-foreground flex items-center gap-2 text-xs">
					<span
						className={`flex items-center gap-1 ${step === 'pick' ? 'text-foreground font-medium' : 'text-success'}`}
					>
						{step === 'fill' ? (
							<Check className="h-3 w-3" />
						) : (
							<span className="flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px]">
								1
							</span>
						)}
						Choose API
					</span>
					<ChevronRight className="h-3 w-3" />
					<span
						className={`flex items-center gap-1 ${step === 'fill' ? 'text-foreground font-medium' : ''}`}
					>
						<span className="flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px]">
							2
						</span>
						Enter credentials
					</span>
				</div>
			)}

			<div className="bg-muted border-border rounded-xl border p-6">
				{step === 'pick' && <ApiPicker onSelect={handleApiSelect} />}
				{step === 'fill' && selectedApi && (
					<CredentialFields
						selectedApi={selectedApi}
						onBack={() => setStep('pick')}
						onSaved={() => navigate('/credentials')}
						editId={id}
						existing={existing}
					/>
				)}
				{step === 'fill' && !selectedApi && isEdit && (
					<div className="flex items-center justify-center py-8">
						<Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />
					</div>
				)}
			</div>
		</div>
	);
}
