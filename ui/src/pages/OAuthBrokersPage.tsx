import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
	Link2,
	Plus,
	Trash2,
	RefreshCw,
	RotateCcw,
	ExternalLink,
	ChevronDown,
	ChevronRight,
	Shield,
} from 'lucide-react';
import { oauthBrokers } from '@/api/client';
import type { OAuthBroker, ConnectLinkResponse } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Label } from '@/components/ui/Label';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { ConfirmInline } from '@/components/ui/ConfirmInline';
import { AppLink } from '@/components/ui/AppLink';
import { useAuth } from '@/hooks/useAuth';

// ── Add Broker Form ──────────────────────────────────────────────

function AddBrokerForm({ onClose }: { onClose: () => void }) {
	const queryClient = useQueryClient();
	const [form, setForm] = useState({
		id: '',
		type: 'pipedream',
		client_id: '',
		client_secret: '',
		project_id: '',
		environment: 'production',
		default_external_user_id: 'default',
	});

	const createMutation = useMutation({
		mutationFn: () =>
			oauthBrokers.create({
				id: form.id,
				type: form.type,
				config: {
					client_id: form.client_id,
					client_secret: form.client_secret,
					project_id: form.project_id,
					environment: form.environment,
					default_external_user_id: form.default_external_user_id,
				},
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] });
			onClose();
		},
	});

	const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
		setForm((f) => ({ ...f, [field]: e.target.value }));

	return (
		<div className="bg-muted border-border space-y-4 rounded-xl border p-4">
			<h2 className="text-foreground text-sm font-medium">Add OAuth Broker</h2>

			<div className="grid grid-cols-2 gap-3">
				<div>
					<Label htmlFor="broker-id" className="text-muted-foreground mb-1 block text-xs">
						Broker ID
					</Label>
					<Input
						id="broker-id"
						value={form.id}
						onChange={set('id')}
						placeholder="e.g. pipedream"
					/>
				</div>
				<div>
					<Label
						htmlFor="broker-type"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Type
					</Label>
					<Select id="broker-type" value={form.type} onChange={set('type')}>
						<option value="pipedream">pipedream</option>
					</Select>
				</div>
				<div>
					<Label
						htmlFor="broker-client-id"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Client ID
					</Label>
					<Input
						id="broker-client-id"
						value={form.client_id}
						onChange={set('client_id')}
						placeholder="OAuth client ID"
					/>
				</div>
				<div>
					<Label
						htmlFor="broker-client-secret"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Client Secret
					</Label>
					<Input
						id="broker-client-secret"
						type="password"
						value={form.client_secret}
						onChange={set('client_secret')}
						placeholder="OAuth client secret"
					/>
				</div>
				<div>
					<Label
						htmlFor="broker-project-id"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Project ID
					</Label>
					<Input
						id="broker-project-id"
						value={form.project_id}
						onChange={set('project_id')}
						placeholder="Pipedream project ID"
					/>
				</div>
				<div>
					<Label
						htmlFor="broker-environment"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Environment
					</Label>
					<Input
						id="broker-environment"
						value={form.environment}
						onChange={set('environment')}
					/>
				</div>
				<div className="col-span-2">
					<Label
						htmlFor="broker-ext-user-id"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Default External User ID
					</Label>
					<Input
						id="broker-ext-user-id"
						value={form.default_external_user_id}
						onChange={set('default_external_user_id')}
					/>
				</div>
			</div>

			{createMutation.isError && (
				<p role="alert" className="text-danger text-xs">
					{(createMutation.error as Error).message}
				</p>
			)}

			<div className="flex items-center gap-2">
				<Button
					onClick={() => createMutation.mutate()}
					loading={createMutation.isPending}
					disabled={
						!form.id || !form.client_id || !form.client_secret || !form.project_id
					}
				>
					Create Broker
				</Button>
				<Button variant="ghost" onClick={onClose}>
					Cancel
				</Button>
			</div>
		</div>
	);
}

// ── Connect Account Panel ────────────────────────────────────────

function CatalogSearch({
	onSelect,
	mirrorValue,
}: {
	onSelect: (apiId: string) => void;
	mirrorValue?: string;
}) {
	const [q, setQ] = useState('');
	const [dirty, setDirty] = useState(false);
	const [selected, setSelected] = useState('');

	// Mirror the slug value unless user has manually edited the search field
	useEffect(() => {
		if (!dirty && mirrorValue !== undefined) {
			setQ(mirrorValue);
		}
	}, [mirrorValue, dirty]);

	const { data, isLoading } = useQuery({
		queryKey: ['catalog-search', q],
		queryFn: () =>
			fetch(`/catalog?q=${encodeURIComponent(q)}&limit=10`, { credentials: 'include' }).then(
				(r) => r.json(),
			),
		enabled: q.length >= 2,
	});

	const entries: any[] = data?.data ?? [];

	if (selected) {
		return (
			<div className="flex items-center gap-2">
				<span className="bg-muted rounded px-2 py-1 font-mono text-xs">{selected}</span>
				<Button
					variant="ghost"
					size="sm"
					className="text-muted-foreground text-xs underline"
					onClick={() => {
						setSelected('');
						onSelect('');
					}}
				>
					change
				</Button>
			</div>
		);
	}

	return (
		<div className="space-y-1.5">
			<Input
				id="broker-catalog-api"
				className="bg-background border-border text-foreground placeholder:text-muted-foreground/50 focus:ring-primary/50 w-full rounded-lg border px-3 py-2 text-sm focus:ring-1 focus:outline-hidden"
				value={q}
				onChange={(e) => {
					setQ(e.target.value);
					if (e.target.value === '') {
						setDirty(false);
					} else {
						setDirty(true);
					}
					setSelected('');
				}}
				placeholder="Search catalog, e.g. gmail, slack, github"
			/>
			{q.length >= 2 && (
				<div className="border-border max-h-40 overflow-hidden overflow-y-auto rounded-lg border">
					{isLoading ? (
						<p className="text-muted-foreground p-2 text-xs">Searching...</p>
					) : entries.length === 0 ? (
						<p className="text-muted-foreground p-2 text-xs">No results for "{q}"</p>
					) : (
						entries.map((e: any) => (
							<Button
								variant="ghost"
								size="sm"
								key={e.api_id}
								className="hover:bg-muted border-border w-full justify-start border-b px-3 py-2 text-left font-mono text-xs last:border-0"
								onClick={() => {
									setSelected(e.api_id);
									setQ('');
									onSelect(e.api_id);
								}}
							>
								{e.api_id}
							</Button>
						))
					)}
				</div>
			)}
		</div>
	);
}

function ConnectAccountPanel({
	brokerId,
	externalUserId,
	onDone,
}: {
	brokerId: string;
	externalUserId: string;
	onDone?: () => void;
}) {
	const [appSlug, setAppSlug] = useState('');
	const [label, setLabel] = useState('');
	const [apiId, setApiId] = useState('');
	const [connectLink, setConnectLink] = useState<ConnectLinkResponse | null>(null);

	const linkMutation = useMutation({
		mutationFn: () =>
			oauthBrokers.connectLink(brokerId, {
				app: appSlug,
				external_user_id: externalUserId,
				label: label || appSlug,
				api_id: apiId || undefined,
			}),
		onSuccess: (data) => setConnectLink(data),
	});

	if (connectLink) {
		return (
			<div className="bg-background border-primary/30 space-y-3 rounded-xl border p-4">
				<p className="text-foreground text-sm font-medium">Connect your account</p>
				<AppLink
					href={connectLink.connect_link_url}
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
				>
					<ExternalLink className="h-4 w-4" />
					Open Connect Link
				</AppLink>
				<p className="text-muted-foreground text-xs">
					Click the link above to connect your account in Pipedream. Return here and click{' '}
					<strong>Done</strong> when finished — this will sync your new connection
					automatically.
				</p>
				<Button
					variant="ghost"
					size="sm"
					onClick={() => {
						setConnectLink(null);
						onDone?.();
					}}
				>
					Done — Sync Now
				</Button>
			</div>
		);
	}

	return (
		<div className="bg-background border-border space-y-3 rounded-xl border p-4">
			<p className="text-foreground text-sm font-medium">Connect a new account</p>
			<div className="grid grid-cols-2 gap-3">
				<div>
					<Label
						htmlFor="broker-app-slug"
						className="text-muted-foreground mb-1 block text-xs"
					>
						App Slug
					</Label>
					<Input
						id="broker-app-slug"
						value={appSlug}
						onChange={(e) => setAppSlug(e.target.value)}
						placeholder="e.g. gmail, slack, github"
					/>
				</div>
				<div>
					<Label
						htmlFor="broker-label"
						className="text-muted-foreground mb-1 block text-xs"
					>
						Label (optional)
					</Label>
					<Input
						id="broker-label"
						value={label}
						onChange={(e) => setLabel(e.target.value)}
						placeholder="e.g. My Gmail"
					/>
				</div>
			</div>
			<div>
				<Label
					htmlFor="broker-catalog-api"
					className="text-muted-foreground mb-1 block text-xs"
				>
					Catalog API <span className="text-danger">*</span>
				</Label>
				<CatalogSearch onSelect={setApiId} mirrorValue={appSlug} />
			</div>
			{linkMutation.isError && (
				<p className="text-danger text-xs">{(linkMutation.error as Error).message}</p>
			)}
			<Button
				size="sm"
				onClick={() => linkMutation.mutate()}
				loading={linkMutation.isPending}
				disabled={!appSlug || !apiId}
			>
				<ExternalLink className="h-3.5 w-3.5" /> Get Connect Link
			</Button>
		</div>
	);
}

// ── Broker Accounts Section ──────────────────────────────────────

function BrokerAccounts({ broker }: { broker: OAuthBroker }) {
	const queryClient = useQueryClient();
	const externalUserId = broker.config?.default_external_user_id ?? 'default';
	const [showConnect, setShowConnect] = useState(false);
	const [confirmDeleteAccount, setConfirmDeleteAccount] = useState<string | null>(null);

	const {
		data: accounts,
		isLoading,
		isError: accountsError,
	} = useQuery({
		queryKey: ['oauth-broker-accounts', broker.id],
		queryFn: () => oauthBrokers.accounts(broker.id, externalUserId),
	});

	const syncMutation = useMutation({
		mutationFn: () => oauthBrokers.sync(broker.id, externalUserId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['oauth-broker-accounts', broker.id] });
		},
	});

	const deleteAccountMutation = useMutation({
		mutationFn: (accountId: string) => oauthBrokers.deleteAccount(broker.id, accountId),
		onSuccess: () => {
			setConfirmDeleteAccount(null);
			queryClient.invalidateQueries({ queryKey: ['oauth-broker-accounts', broker.id] });
		},
	});

	const [reconnectLink, setReconnectLink] = useState<{ accountId: string; url: string } | null>(
		null,
	);
	const reconnectMutation = useMutation({
		mutationFn: (accountId: string) => oauthBrokers.reconnectLink(broker.id, accountId),
		onSuccess: (data, accountId) => setReconnectLink({ accountId, url: data.connect_link_url }),
	});

	return (
		<div className="mt-3 space-y-3 pl-8">
			<div className="flex items-center gap-2">
				<h3 className="text-muted-foreground font-mono text-xs tracking-widest uppercase">
					Connected Accounts
				</h3>
				<Button
					variant="secondary"
					size="sm"
					onClick={() => syncMutation.mutate()}
					loading={syncMutation.isPending}
				>
					<RefreshCw className="h-3.5 w-3.5" /> Sync
				</Button>
				<Button variant="secondary" size="sm" onClick={() => setShowConnect((s) => !s)}>
					<Plus className="h-3.5 w-3.5" /> Connect Account
				</Button>
			</div>

			{syncMutation.isSuccess && (
				<p className="text-success text-xs">
					Synced — {syncMutation.data.accounts_synced} account(s) updated.
				</p>
			)}

			{showConnect && (
				<ConnectAccountPanel
					brokerId={broker.id}
					externalUserId={externalUserId}
					onDone={() => {
						setShowConnect(false);
						syncMutation.mutate();
					}}
				/>
			)}

			{isLoading ? (
				<p className="text-muted-foreground text-xs">Loading accounts...</p>
			) : accountsError ? (
				<p className="text-danger text-xs">Failed to load accounts.</p>
			) : !Array.isArray(accounts) || accounts.length === 0 ? (
				<p className="text-muted-foreground text-xs">
					No connected accounts yet. Use Sync or Connect Account above.
				</p>
			) : (
				<div className="space-y-1.5">
					{accounts.map((acc) => (
						<div
							key={`${acc.account_id ?? ''}-${acc.api_host}`}
							className="border-border overflow-hidden rounded-lg border"
						>
							<div className="bg-background flex items-center gap-3 p-3 text-sm">
								<Shield className="text-accent-teal h-4 w-4 shrink-0" />
								<div className="min-w-0 flex-1">
									<div className="flex flex-wrap items-center gap-2">
										<span className="text-foreground font-medium">
											{acc.label || acc.app_slug}
										</span>
										<Badge variant="default" className="text-[10px]">
											{acc.app_slug}
										</Badge>
										{acc.api_host && (
											<span className="text-muted-foreground font-mono text-xs">
												{acc.api_host}
											</span>
										)}
									</div>
									<div className="mt-0.5 flex items-center gap-3">
										<span className="text-muted-foreground text-xs">
											account: {acc.account_id}
										</span>
										{acc.synced_at && (
											<span className="text-muted-foreground text-xs">
												synced{' '}
												{new Date(
													Number(acc.synced_at) * 1000,
												).toLocaleString()}
											</span>
										)}
									</div>
								</div>
								<Button
									variant="ghost"
									size="sm"
									className="text-muted-foreground hover:text-foreground shrink-0"
									onClick={() => reconnectMutation.mutate(acc.account_id)}
									loading={
										reconnectMutation.isPending &&
										reconnectMutation.variables === acc.account_id
									}
									aria-label="Reconnect account"
									title="Reconnect — re-authorise this account via OAuth"
								>
									<RotateCcw className="h-3.5 w-3.5" />
								</Button>
								<Button
									variant="ghost"
									size="sm"
									className="text-destructive hover:text-destructive shrink-0"
									onClick={() =>
										setConfirmDeleteAccount(acc.account_id ?? acc.api_host)
									}
									aria-label="Remove account"
								>
									<Trash2 className="h-3.5 w-3.5" />
								</Button>
							</div>

							{reconnectLink?.accountId === acc.account_id && (
								<div className="bg-background border-primary/30 space-y-3 border-t p-3 text-xs">
									<p className="text-foreground font-medium">
										Re-authorise {acc.label ?? acc.app_slug}
									</p>
									<p className="text-muted-foreground">
										Click the link to complete OAuth. The old connection will be
										removed automatically once the new one is confirmed.
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

							{confirmDeleteAccount === (acc.account_id ?? acc.api_host) && (
								<div className="bg-destructive/5 border-border space-y-2 border-t px-3 pt-1 pb-3 text-xs">
									<p className="text-destructive font-medium">
										Remove this connection?
									</p>
									<p className="text-muted-foreground">This will:</p>
									<ul className="text-muted-foreground ml-1 list-inside list-disc space-y-0.5">
										<li>
											Revoke <strong>{acc.label || acc.app_slug}</strong> in
											Pipedream (upstream provider)
										</li>
										<li>
											Remove the credential from any toolkits it's provisioned
											to
										</li>
										<li>Delete the credential from this instance</li>
									</ul>
									{deleteAccountMutation.isError && (
										<p className="text-destructive">
											{String(deleteAccountMutation.error)}
										</p>
									)}
									<div className="flex gap-2 pt-1">
										<Button
											variant="danger"
											size="sm"
											loading={deleteAccountMutation.isPending}
											onClick={() =>
												deleteAccountMutation.mutate(acc.account_id)
											}
										>
											Remove & Revoke
										</Button>
										<Button
											variant="ghost"
											size="sm"
											onClick={() => setConfirmDeleteAccount(null)}
										>
											Cancel
										</Button>
									</div>
								</div>
							)}
						</div>
					))}
				</div>
			)}
		</div>
	);
}

// ── Broker Card ──────────────────────────────────────────────────

function BrokerCard({ broker }: { broker: OAuthBroker }) {
	const queryClient = useQueryClient();
	const [expanded, setExpanded] = useState(false);

	const deleteMutation = useMutation({
		mutationFn: () => oauthBrokers.delete(broker.id),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] }),
	});

	return (
		<div className="bg-muted border-border rounded-xl border p-4">
			<div className="flex items-center gap-3">
				<Button
					variant="ghost"
					size="icon"
					onClick={() => setExpanded((e) => !e)}
					className="text-muted-foreground hover:text-foreground transition-colors"
					aria-label={expanded ? 'Collapse broker details' : 'Expand broker details'}
					aria-expanded={expanded}
				>
					{expanded ? (
						<ChevronDown className="h-5 w-5" />
					) : (
						<ChevronRight className="h-5 w-5" />
					)}
				</Button>
				<Link2 className="text-accent-blue h-5 w-5 shrink-0" />
				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-center gap-2">
						<span className="text-foreground font-medium">{broker.id}</span>
						<Badge variant="default" className="text-[10px]">
							{broker.type}
						</Badge>
						{broker.config?.project_id && (
							<span className="text-muted-foreground font-mono text-xs">
								project: {broker.config.project_id}
							</span>
						)}
					</div>
					<div className="mt-0.5 flex items-center gap-3">
						{broker.config?.default_external_user_id && (
							<span className="text-muted-foreground text-xs">
								user: {broker.config.default_external_user_id}
							</span>
						)}
						{broker.created_at && (
							<span className="text-muted-foreground text-xs">
								created{' '}
								{new Date(Number(broker.created_at) * 1000).toLocaleDateString()}
							</span>
						)}
					</div>
				</div>
				<ConfirmInline
					onConfirm={() => deleteMutation.mutate()}
					message="Delete this broker?"
					confirmLabel="Delete"
				>
					<Button variant="danger" size="sm" aria-label="Delete broker">
						<Trash2 className="h-4 w-4" />
					</Button>
				</ConfirmInline>
			</div>

			{expanded && <BrokerAccounts broker={broker} />}
		</div>
	);
}

// ── Main Page ────────────────────────────────────────────────────

export default function OAuthBrokersPage() {
	const [showAdd, setShowAdd] = useState(false);
	const { user } = useAuth();

	const {
		data: brokersRaw,
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['oauth-brokers'],
		queryFn: () => oauthBrokers.list(),
		enabled: !!user?.logged_in,
	});
	const brokers = Array.isArray(brokersRaw) ? brokersRaw : [];

	return (
		<div className="max-w-5xl space-y-5">
			<PageHeader
				category="Management"
				title="OAuth Brokers"
				actions={
					<Button onClick={() => setShowAdd((s) => !s)} aria-expanded={showAdd}>
						<Plus className="h-4 w-4" /> Add Broker
					</Button>
				}
			/>

			<div className="bg-muted border-border text-muted-foreground rounded-xl border p-4 text-sm">
				Manage OAuth brokers for delegated API authentication. Connect external accounts
				through providers like Pipedream and sync them for agent use.
			</div>

			{showAdd && <AddBrokerForm onClose={() => setShowAdd(false)} />}

			{isLoading || !user?.logged_in ? (
				<LoadingState message="Loading brokers..." />
			) : isError ? (
				<ErrorAlert message="Failed to load OAuth brokers. Please try refreshing the page." />
			) : !brokers || brokers.length === 0 ? (
				<EmptyState
					icon={<Link2 className="h-10 w-10 opacity-30" />}
					title="No OAuth brokers configured"
					description="Add a broker to connect external accounts for agent OAuth access."
					action={<Button onClick={() => setShowAdd(true)}>Add your first broker</Button>}
				/>
			) : (
				<div className="space-y-2">
					{brokers.map((broker) => (
						<BrokerCard key={broker.id} broker={broker} />
					))}
				</div>
			)}
		</div>
	);
}
