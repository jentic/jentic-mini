import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Trash2, Settings, RotateCcw, ExternalLink, Link2 } from 'lucide-react';
import { api, oauthBrokers } from '@/api/client';
import type { OAuthBroker } from '@/api/client';
import { AppLink } from '@/components/ui/AppLink';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { ConfirmInline } from '@/components/ui/ConfirmInline';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { useAuth } from '@/hooks/useAuth';

function formatSyncedAt(ts: number): string {
	return new Date(ts * 1000).toLocaleString();
}

// ── Pipedream Setup / Edit Form ───────────────────────────────────────────────
// This component owns both the save and delete mutations so they can't be
// destabilised by parent re-renders that occur when query invalidation fires.

function PipedreamForm({
	existing,
	onClose,
	onDeleted,
}: {
	existing?: OAuthBroker;
	onClose: () => void;
	onDeleted?: () => void; // called after successful delete
}) {
	const queryClient = useQueryClient();
	const [form, setForm] = useState({
		client_id: existing?.config?.client_id ?? '',
		client_secret: '',
		project_id: existing?.config?.project_id ?? '',
	});
	const [confirmDelete, setConfirmDelete] = useState(false);

	const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
		setForm((f) => ({ ...f, [field]: e.target.value }));

	const saveMutation = useMutation({
		mutationFn: () =>
			existing
				? oauthBrokers.update('pipedream', {
						client_id: form.client_id || undefined,
						client_secret: form.client_secret || undefined,
						project_id: form.project_id || undefined,
				  })
				: oauthBrokers.create({
						id: 'pipedream',
						type: 'pipedream',
						config: {
							client_id: form.client_id,
							client_secret: form.client_secret,
							project_id: form.project_id,
						},
				  }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] });
			onClose();
		},
	});

	const deleteMutation = useMutation({
		mutationFn: () => oauthBrokers.delete('pipedream'),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] });
			queryClient.invalidateQueries({ queryKey: ['credentials'] });
			onDeleted?.();
		},
	});

	const isNew = !existing;
	const canSubmit = isNew
		? !!(form.client_id && form.client_secret && form.project_id)
		: !!(form.client_id || form.client_secret || form.project_id);

	return (
		<div className="bg-muted border-border space-y-4 rounded-xl border p-5">
			<h2 className="text-foreground text-sm font-semibold">
				{isNew ? 'Enable OAuth with Pipedream' : 'Edit Pipedream configuration'}
			</h2>

			{isNew && (
				<div className="bg-background border-border space-y-2 rounded-lg border p-4 text-xs">
					<p className="text-foreground font-medium">One-time Pipedream setup</p>
					<ol className="text-muted-foreground ml-4 list-decimal space-y-1.5">
						<li>
							Go to{' '}
							<AppLink href="https://pipedream.com" className="text-primary underline">
								pipedream.com
							</AppLink>{' '}
							and sign in or create an account.
						</li>
						<li>
							Go to <strong>Settings → API</strong> → click{' '}
							<strong>+ New OAuth Client</strong>. Name it <em>Jentic</em>. Copy the{' '}
							<strong>Client ID</strong> and <strong>Client Secret</strong> — the
							secret is not shown again.
						</li>
						<li>
							Go to <strong>Projects → + New Project</strong>. Name it <em>Jentic</em>
							. Open its <strong>Settings</strong> and copy the{' '}
							<strong>Project ID</strong> (format: <code>proj_xxx</code>).
						</li>
					</ol>
					<p className="text-muted-foreground mt-1">
						Jentic automatically configures the Connect application name and logo in
						Pipedream — you don't need to touch the Connect → Configuration screen.
					</p>
				</div>
			)}

			<div className="grid grid-cols-2 gap-3">
				<div>
					<Label htmlFor="pd-client-id" className="text-muted-foreground mb-1 block text-xs">
						Client ID
					</Label>
					<Input
						id="pd-client-id"
						value={form.client_id}
						onChange={set('client_id')}
						placeholder={existing ? '(unchanged)' : 'AbCdEfGhIjKlMnOpQrStUvWxYz012345'}
					/>
				</div>
				<div>
					<Label
						htmlFor="pd-client-secret"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Client Secret
					</Label>
					<Input
						id="pd-client-secret"
						type="password"
						value={form.client_secret}
						onChange={set('client_secret')}
						placeholder={existing ? '(unchanged)' : 'abc-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-de-fghij'}
					/>
				</div>
				<div className="col-span-2">
					<Label
						htmlFor="pd-project-id"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Project ID
					</Label>
					<Input
						id="pd-project-id"
						value={form.project_id}
						onChange={set('project_id')}
						placeholder={existing ? '(unchanged)' : 'proj_AbCdEfGhIjKlMnOpQrStUvWxYz01'}
					/>
				</div>
			</div>

			{saveMutation.isError && (
				<p role="alert" className="text-danger text-xs">
					{(saveMutation.error as Error).message}
				</p>
			)}
			{deleteMutation.isError && (
				<p role="alert" className="text-danger text-xs">
					Failed to remove: {(deleteMutation.error as Error).message}
				</p>
			)}

			<div className="flex items-center justify-between gap-2">
				<div className="flex items-center gap-2">
					<Button
						onClick={() => saveMutation.mutate()}
						loading={saveMutation.isPending}
						disabled={!canSubmit || deleteMutation.isPending}
					>
						{isNew ? 'Enable Pipedream OAuth' : 'Save changes'}
					</Button>
					<Button variant="ghost" onClick={onClose} disabled={saveMutation.isPending || deleteMutation.isPending}>
						Cancel
					</Button>
				</div>
				{existing && (
					<div className="flex items-center gap-2">
						{confirmDelete ? (
							<>
								<span className="text-muted-foreground text-xs">
									Remove Pipedream and all OAuth credentials?
								</span>
								<Button
									variant="danger"
									size="sm"
									loading={deleteMutation.isPending}
									onClick={() => deleteMutation.mutate()}
								>
									Yes, remove
								</Button>
								{!deleteMutation.isPending && (
									<Button
										variant="ghost"
										size="sm"
										onClick={() => setConfirmDelete(false)}
									>
										Cancel
									</Button>
								)}
							</>
						) : (
							<Button
								variant="danger"
								size="sm"
								onClick={() => setConfirmDelete(true)}
								disabled={saveMutation.isPending}
							>
								<Trash2 className="h-4 w-4" /> Remove Pipedream
							</Button>
						)}
					</div>
				)}
			</div>
		</div>
	);
}

// ── Pipedream Status Line ─────────────────────────────────────────────────────
// A single line of muted text above the credentials list — not a card.
// OAuth is an enhancement; this is incidental info, not a peer of the creds.

function PipedreamStatusLine() {
	const [showForm, setShowForm] = useState(false);

	const { data: brokersRaw } = useQuery({
		queryKey: ['oauth-brokers'],
		queryFn: () => oauthBrokers.list(),
	});
	const brokers = Array.isArray(brokersRaw) ? brokersRaw : [];
	const pipedream = brokers.find((b) => b.id === 'pipedream') ?? null;

	const { data: accountsRaw } = useQuery({
		queryKey: ['oauth-broker-accounts', 'pipedream'],
		queryFn: () => oauthBrokers.accounts('pipedream', 'default'),
		enabled: !!pipedream,
	});
	const accounts = Array.isArray(accountsRaw) ? accountsRaw : [];

	const lastSynced =
		accounts.length > 0
			? Math.max(...accounts.map((a) => Number(a.synced_at) || 0))
			: null;

	if (showForm) {
		return (
			<PipedreamForm
				existing={pipedream ?? undefined}
				onClose={() => setShowForm(false)}
				onDeleted={() => setShowForm(false)}
			/>
		);
	}

	if (!pipedream) {
		return (
			<p className="text-muted-foreground text-xs">
				<Link2 className="mr-1 inline h-3 w-3 align-middle opacity-60" />
				OAuth not configured.{' '}
				<button
					onClick={() => setShowForm(true)}
					className="text-primary hover:underline focus:outline-none"
				>
					Enable OAuth via Pipedream
				</button>
				.
			</p>
		);
	}

	return (
		<p className="text-muted-foreground text-xs">
			<Link2 className="text-primary mr-1 inline h-3 w-3 align-middle" />
			OAuth enabled via Pipedream
			{accounts.length > 0 && (
				<span>
					{' · '}
					{accounts.length} account{accounts.length !== 1 ? 's' : ''}
				</span>
			)}
			{lastSynced && <span>{' · '}last synced {formatSyncedAt(lastSynced)}</span>}
			{' · '}
			<button
				onClick={() => setShowForm(true)}
				className="text-primary hover:underline focus:outline-none"
			>
				edit
			</button>
		</p>
	);
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CredentialsPage() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const { user } = useAuth();

	const {
		data: credentials = [],
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['credentials'],
		queryFn: () => api.listCredentials(),
		select: (d: any) => (Array.isArray(d) ? d : Array.isArray(d?.data) ? d.data : []),
		enabled: !!user?.logged_in,
	});

	const deleteMutation = useMutation({
		mutationFn: (cred: {
			id: string;
			authType: string;
			brokerId?: string;
			accountId?: string;
		}) => {
			if (cred.authType === 'pipedream_oauth' && cred.brokerId && cred.accountId) {
				return oauthBrokers.deleteAccount(cred.brokerId, cred.accountId);
			}
			return api.deleteCredential(cred.id);
		},
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
	});

	const [reconnectLink, setReconnectLink] = useState<{ credId: string; url: string } | null>(
		null,
	);
	const reconnectMutation = useMutation({
		mutationFn: ({ brokerId, accountId }: { brokerId: string; accountId: string }) =>
			oauthBrokers.reconnectLink(brokerId, accountId),
		onSuccess: (data: any, vars) => {
			setReconnectLink({ credId: vars.accountId, url: data.connect_link_url });
		},
	});

	return (
		<div className="max-w-5xl space-y-5">
			<PageHeader
				category="Management"
				title="Credentials Vault"
				actions={
					<Button onClick={() => navigate('/credentials/new')}>
						<Plus className="h-4 w-4" /> Add Credential
					</Button>
				}
			/>

			{isLoading || !user?.logged_in ? (
				<LoadingState message="Loading credentials..." />
			) : isError ? (
				<ErrorAlert message="Failed to load credentials. Please try refreshing the page." />
			) : !credentials || credentials.length === 0 ? (
				<>
					<PipedreamStatusLine />
					<EmptyState
						icon={<Key className="h-10 w-10 opacity-30" />}
						title="No credentials stored"
						description="Add a credential to authenticate agents with external APIs."
						action={
							<Button onClick={() => navigate('/credentials/new')}>
								Add your first credential
							</Button>
						}
					/>
				</>
			) : (
				<div className="space-y-3">
					<PipedreamStatusLine />
					<div className="space-y-2">
						{credentials.map((cred: any) => (
							<div
								key={cred.id}
								className="bg-muted border-border rounded-xl border p-4"
							>
								<div className="flex items-center gap-3">
									<Key className="text-accent-yellow h-5 w-5 shrink-0" />
									<div className="min-w-0 flex-1">
										<div className="flex flex-wrap items-center gap-2">
											<span className="text-foreground font-medium">
												{cred.label}
											</span>
											{cred.app_slug && (
												<span className="text-muted-foreground text-xs">
													({cred.app_slug})
												</span>
											)}
											{cred.api_id && (
												<span className="text-muted-foreground font-mono text-xs">
													{cred.api_id}
												</span>
											)}
											{cred.auth_type === 'pipedream_oauth' ? (
												<Badge variant="default" className="text-[10px]">
													OAuth via Pipedream
												</Badge>
											) : cred.scheme_name ? (
												<Badge variant="default" className="text-[10px]">
													{cred.scheme_name}
												</Badge>
											) : null}
										</div>
										<p className="text-muted-foreground mt-0.5 text-xs">
											{cred.auth_type === 'pipedream_oauth' &&
											cred.account_id ? (
												<>
													<span>account: {cred.account_id}</span>
													{cred.synced_at && (
														<span className="ml-2">
															synced {formatSyncedAt(cred.synced_at)}
														</span>
													)}
												</>
											) : cred.created_at ? (
												<span>
													Added{' '}
													{new Date(
														cred.created_at * 1000,
													).toLocaleDateString()}
												</span>
											) : null}
										</p>
									</div>
									<div className="flex items-center gap-2">
										{cred.auth_type === 'pipedream_oauth' ? (
											<Button
												variant="secondary"
												size="sm"
												onClick={() => {
													if (
														reconnectLink?.credId === cred.account_id
													) {
														setReconnectLink(null);
													} else {
														reconnectMutation.mutate({
															brokerId: 'pipedream',
															accountId: cred.account_id,
														});
													}
												}}
												disabled={
													reconnectMutation.isPending &&
													reconnectMutation.variables?.accountId ===
														cred.account_id
												}
											>
												<RotateCcw className="h-4 w-4" /> Reconnect
											</Button>
										) : (
											<Button
												variant="secondary"
												size="sm"
												onClick={() =>
													navigate(
														`/credentials/${encodeURIComponent(cred.id)}/edit`,
													)
												}
											>
												<Settings className="h-4 w-4" /> Edit
											</Button>
										)}
										<ConfirmInline
											onConfirm={() =>
												deleteMutation.mutate({
													id: cred.id,
													authType: cred.auth_type,
													brokerId:
														cred.auth_type === 'pipedream_oauth'
															? 'pipedream'
															: undefined,
													accountId:
														cred.auth_type === 'pipedream_oauth'
															? cred.account_id
															: undefined,
												})
											}
											message="Delete this credential?"
											confirmLabel="Delete"
										>
											<Button variant="danger" size="sm">
												<Trash2 className="h-4 w-4" />
											</Button>
										</ConfirmInline>
									</div>
								</div>
								{reconnectLink?.credId === cred.account_id && (
									<div className="bg-background border-primary/30 mt-3 space-y-3 border-t p-3 text-xs">
										<p className="text-foreground font-medium">
											Re-authorise {cred.label}
										</p>
										<p className="text-muted-foreground">
											Click the link to complete OAuth. The old connection
											will be removed automatically once the new one is
											confirmed.
										</p>
										<div className="flex items-center gap-2">
											<AppLink
												href={reconnectLink.url}
												className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
											>
												<ExternalLink className="h-3.5 w-3.5" />
												Open Reconnect Link
											</AppLink>
											<Button
												variant="ghost"
												size="sm"
												onClick={() => setReconnectLink(null)}
											>
												Cancel
											</Button>
										</div>
									</div>
								)}
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}
