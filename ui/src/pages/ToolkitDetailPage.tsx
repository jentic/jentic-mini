import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
	ChevronLeft,
	Key,
	Plus,
	Trash2,
	Settings,
	AlertTriangle,
	Link as LinkIcon,
	X,
	Unlink,
	Edit2,
	ChevronDown,
	ChevronUp,
	Save,
	Ban,
	ShieldCheck,
} from 'lucide-react';
import { api } from '@/api/client';
import type { KeyCreate } from '@/api/types';
import { OneTimeKeyDisplay } from '@/components/ui/OneTimeKeyDisplay';
import { ConfirmInline } from '@/components/ui/ConfirmInline';
import { Badge } from '@/components/ui/Badge';
import { PermissionRuleEditor } from '@/components/ui/PermissionRuleEditor';

function CredentialPermissionEditor({
	toolkitId,
	credential,
	onClose,
}: {
	toolkitId: string;
	credential: any;
	onClose: () => void;
}) {
	const queryClient = useQueryClient();
	const [rules, setRules] = useState<any[]>([]);

	const {
		data: permissions,
		isLoading,
		isError,
	} = useQuery({
		queryKey: ['permissions', toolkitId, credential.credential_id],
		queryFn: () => api.getPermissions(toolkitId, credential.credential_id),
	});

	React.useEffect(() => {
		if (permissions) {
			const agentRules = Array.isArray(permissions)
				? permissions.filter((r: any) => !r._comment?.includes('System safety'))
				: [];
			setRules(agentRules);
		}
	}, [permissions]);

	const saveMutation = useMutation({
		mutationFn: () => api.setPermissions(toolkitId, credential.credential_id, rules),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['toolkit', toolkitId] });
			queryClient.invalidateQueries({
				queryKey: ['permissions', toolkitId, credential.credential_id],
			});
			onClose();
		},
	});

	if (isLoading)
		return (
			<div className="border-border bg-background/50 border-t p-5">
				<p className="text-muted-foreground text-sm">Loading permissions...</p>
			</div>
		);

	if (isError)
		return (
			<div className="border-border bg-background/50 border-t p-5">
				<p className="text-danger text-sm">Failed to load permissions.</p>
			</div>
		);

	return (
		<div className="border-border bg-background/50 space-y-4 border-t p-5">
			<div className="flex items-start justify-between gap-2">
				<div>
					<p className="text-foreground text-sm font-semibold">
						Permission Rules for {credential.label}
					</p>
					<p className="text-muted-foreground mt-0.5 text-xs">
						Define which operations this credential can access. System safety rules are
						always appended.
					</p>
				</div>
				<button
					type="button"
					onClick={onClose}
					className="text-muted-foreground hover:text-foreground shrink-0"
				>
					<X className="h-4 w-4" />
				</button>
			</div>

			<PermissionRuleEditor rules={rules} onChange={setRules} />

			<div className="flex gap-2 pt-2">
				<button
					type="button"
					onClick={() => saveMutation.mutate()}
					disabled={saveMutation.isPending}
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
				>
					<Save className="h-4 w-4" />{' '}
					{saveMutation.isPending ? 'Saving...' : 'Save Rules'}
				</button>
				<button
					type="button"
					onClick={onClose}
					className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-4 py-2 text-sm transition-colors"
				>
					Cancel
				</button>
			</div>

			<div className="border-border/50 border-t pt-3">
				<p className="text-muted-foreground text-xs leading-relaxed">
					<strong>Rules syntax:</strong> Each rule has{' '}
					<code className="bg-muted rounded px-1 font-mono">effect</code> (allow/deny),
					optional <code className="bg-muted rounded px-1 font-mono">methods</code> (GET,
					POST, etc.), and optional{' '}
					<code className="bg-muted rounded px-1 font-mono">path</code> regex. Rules are
					evaluated in order. First match wins.
				</p>
			</div>
		</div>
	);
}

function RequestAccessDialog({ toolkitId, onClose }: { toolkitId: string; onClose: () => void }) {
	const queryClient = useQueryClient();
	const [requestType, setRequestType] = useState<'grant' | 'modify_permissions'>('grant');
	const [credentialId, setCredentialId] = useState('');
	const [reason, setReason] = useState('');
	const [rules, setRules] = useState<any[]>([{ effect: 'allow', path: '', methods: [] }]);
	const [error, setError] = useState<string | null>(null);

	const { data: credentials } = useQuery({
		queryKey: ['credentials'],
		queryFn: () => api.listCredentials(),
	});

	const createMutation = useMutation({
		mutationFn: () =>
			api.createAccessRequest(toolkitId, {
				type: requestType,
				credential_id: credentialId,
				rules,
				reason: reason || null,
			}),
		onSuccess: (data: any) => {
			queryClient.invalidateQueries({ queryKey: ['access-requests', toolkitId] });
			alert(
				`Access request created!\n\nApproval URL: ${data.approve_url || data._links?.approve_ui || 'Check pending requests'}`,
			);
			onClose();
		},
		onError: (e: Error) => setError(e.message),
	});

	const credList = Array.isArray(credentials) ? credentials : [];

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center p-4">
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
			<div className="bg-muted border-border relative z-10 max-h-[90vh] w-full max-w-2xl space-y-5 overflow-y-auto rounded-xl border p-6">
				<div className="flex items-center justify-between">
					<h2 className="font-heading text-foreground text-lg font-semibold">
						Request Access
					</h2>
					<button
						type="button"
						onClick={onClose}
						className="text-muted-foreground hover:text-foreground"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<p className="text-muted-foreground text-sm">
					Create an access request for this toolkit. The admin will be notified and can
					approve or deny.
				</p>

				<div className="space-y-4">
					<div>
						<label
							htmlFor="tk-request-type"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Request Type
						</label>
						<select
							id="tk-request-type"
							value={requestType}
							onChange={(e) => setRequestType(e.target.value as any)}
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
						>
							<option value="grant">
								Grant — bind a new credential to this toolkit
							</option>
							<option value="modify_permissions">
								Modify Permissions — update rules on an existing credential
							</option>
						</select>
					</div>

					<div>
						<label
							htmlFor="tk-request-credential"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Credential *
						</label>
						<select
							id="tk-request-credential"
							value={credentialId}
							onChange={(e) => setCredentialId(e.target.value)}
							required
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
						>
							<option value="">Select a credential...</option>
							{credList.map((c: any) => (
								<option key={c.id} value={c.id}>
									{c.label} {c.api_id ? `(${c.api_id})` : ''}
								</option>
							))}
						</select>
					</div>

					<fieldset>
						<legend className="text-muted-foreground mb-1 block text-xs">
							Permission Rules
						</legend>
						<PermissionRuleEditor rules={rules} onChange={setRules} />
					</fieldset>

					<div>
						<label
							htmlFor="tk-request-reason"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Reason (optional)
						</label>
						<textarea
							id="tk-request-reason"
							value={reason}
							onChange={(e) => setReason(e.target.value)}
							rows={2}
							placeholder="Explain why you need this access..."
							className="bg-background border-border text-foreground focus:border-primary w-full resize-none rounded-lg border px-3 py-2 focus:outline-hidden"
						/>
					</div>

					{error && (
						<div className="text-danger bg-danger/10 border-danger/30 flex items-center gap-2 rounded-lg border p-3 text-sm">
							<AlertTriangle className="h-4 w-4 shrink-0" />
							{error}
						</div>
					)}

					<div className="flex gap-2">
						<button
							type="button"
							onClick={() => createMutation.mutate()}
							disabled={!credentialId || createMutation.isPending}
							className="bg-primary text-background hover:bg-primary/80 flex-1 rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50"
						>
							{createMutation.isPending ? 'Submitting...' : 'Submit Request'}
						</button>
						<button
							type="button"
							onClick={onClose}
							className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-4 py-2 transition-colors"
						>
							Cancel
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}

export default function ToolkitDetailPage() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const [showKeyCreate, setShowKeyCreate] = useState(false);
	const [keyName, setKeyName] = useState('');
	const [newKey, setNewKey] = useState<string | null>(null);
	const [showSettings, setShowSettings] = useState(false);
	const [showRequestAccess, setShowRequestAccess] = useState(false);
	const [editName, setEditName] = useState('');
	const [editDesc, setEditDesc] = useState('');
	const [editingPermForCred, setEditingPermForCred] = useState<string | null>(null);

	const { data: toolkit, isLoading } = useQuery({
		queryKey: ['toolkit', id],
		queryFn: () => api.getToolkit(id!),
		enabled: !!id,
		refetchInterval: 30000,
	});

	// FIXED: Keys are NOT returned by get_toolkit; need separate query
	const { data: keysResponse } = useQuery({
		queryKey: ['toolkit-keys', id],
		queryFn: () => api.listKeys(id!),
		enabled: !!id,
		refetchInterval: 30000,
	});

	const { data: pendingReqs } = useQuery({
		queryKey: ['access-requests', id],
		queryFn: () => api.listAccessRequests(id!, 'pending'),
		enabled: !!id,
		refetchInterval: 30000,
	});

	const createKeyMutation = useMutation({
		mutationFn: (d: KeyCreate) => api.createKey(id!, d),
		onSuccess: (data) => {
			setNewKey(data.key);
			setShowKeyCreate(false);
			setKeyName('');
			queryClient.invalidateQueries({ queryKey: ['toolkit-keys', id] });
		},
	});

	const revokeKeyMutation = useMutation({
		mutationFn: (keyId: string) => api.revokeKey(id!, keyId),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['toolkit-keys', id] }),
	});

	const unbindMutation = useMutation({
		mutationFn: (credentialId: string) => api.unbindCredential(id!, credentialId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['toolkit', id] });
		},
	});

	const updateMutation = useMutation({
		mutationFn: () =>
			api.updateToolkit(id!, { name: editName || null, description: editDesc || null }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['toolkit', id] });
			queryClient.invalidateQueries({ queryKey: ['toolkits'] });
			setShowSettings(false);
		},
	});

	const deleteMutation = useMutation({
		mutationFn: () => api.deleteToolkit(id!),
		onSuccess: () => navigate('/toolkits'),
	});

	const [killswitchConfirming, setKillswitchConfirming] = useState(false);
	const killswitchMutation = useMutation({
		mutationFn: (disabled: boolean) => api.updateToolkit(id!, { disabled }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['toolkit', id] });
			queryClient.invalidateQueries({ queryKey: ['toolkits'] });
		},
	});

	React.useEffect(() => {
		if (toolkit && showSettings) {
			setEditName(toolkit.name);
			setEditDesc(toolkit.description ?? '');
		}
	}, [toolkit, showSettings]);

	if (isLoading)
		return <div className="text-muted-foreground py-16 text-center">Loading toolkit...</div>;
	if (!toolkit)
		return (
			<div className="text-muted-foreground py-16 text-center">
				<p>Toolkit not found.</p>
				<button
					type="button"
					onClick={() => navigate('/toolkits')}
					className="bg-muted border-border mt-4 rounded-lg border px-4 py-2 text-sm"
				>
					Back
				</button>
			</div>
		);

	const keys = (keysResponse as any)?.keys ?? [];
	const pending = (pendingReqs ?? []).filter((r: any) => r.status === 'pending');
	const credentials = toolkit.credentials ?? [];

	return (
		<div className="max-w-5xl space-y-6">
			<button
				type="button"
				onClick={() => navigate('/toolkits')}
				className="text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm transition-colors"
			>
				<ChevronLeft className="h-4 w-4" /> Back to Toolkits
			</button>

			<div className="flex flex-wrap items-start justify-between gap-4">
				<div>
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Toolkit
					</p>
					<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
						{toolkit.name}
					</h1>
					{toolkit.description && (
						<p className="text-muted-foreground mt-1">{toolkit.description}</p>
					)}
					<div className="mt-2 flex items-center gap-2">
						{toolkit.simulate && <Badge variant="default">simulate mode</Badge>}
						<span className="text-muted-foreground font-mono text-xs">
							ID: {toolkit.id}
						</span>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<button
						type="button"
						onClick={() => setShowRequestAccess(true)}
						className="bg-primary/10 border-primary/30 text-primary hover:bg-primary/20 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
					>
						<Plus className="h-4 w-4" /> Request Access
					</button>
					{id !== 'default' && (
						<button
							type="button"
							onClick={() => setShowSettings(true)}
							className="bg-muted border-border text-foreground hover:bg-muted/60 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors"
						>
							<Settings className="h-4 w-4" /> Settings
						</button>
					)}
				</div>
			</div>

			{/* Pending requests */}
			{pending.length > 0 && (
				<div className="bg-warning/10 border-warning/30 space-y-3 rounded-xl border p-5">
					<div className="flex items-center gap-2">
						<AlertTriangle className="text-warning h-5 w-5" />
						<h2 className="font-heading text-warning font-semibold">
							{pending.length} Pending Access Request{pending.length !== 1 ? 's' : ''}
						</h2>
					</div>
					{pending.map((req: any) => (
						<div
							key={req.id}
							className="bg-background/40 flex items-center gap-3 rounded-lg px-4 py-3"
						>
							<div className="flex-1">
								<Badge variant={req.type === 'grant' ? 'default' : 'pending'}>
									{req.type === 'grant'
										? 'credential access'
										: 'permission change'}
								</Badge>
								{req.reason && (
									<p className="text-muted-foreground mt-0.5 text-xs">
										{req.reason}
									</p>
								)}
							</div>
							<button
								type="button"
								onClick={() => navigate(`/approve/${toolkit.id}/${req.id}`)}
								className="bg-primary text-background hover:bg-primary/80 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
							>
								Review
							</button>
						</div>
					))}
				</div>
			)}

			{/* API Keys */}
			<div
				className={`overflow-hidden rounded-xl border ${toolkit.disabled ? 'border-danger/50' : 'border-border'} bg-muted`}
			>
				<div
					className={`flex items-center justify-between gap-3 px-5 py-4 ${killswitchConfirming || toolkit.disabled ? 'border-b' : ''} ${toolkit.disabled ? 'border-danger/30 bg-danger/5' : 'border-border'}`}
				>
					<div className="flex items-center gap-2">
						<h3 className="font-heading text-foreground font-semibold">
							API Keys ({keys.length})
						</h3>
						{toolkit.disabled && (
							<span className="bg-danger/15 text-danger border-danger/30 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs">
								<Ban className="h-3 w-3" />
								Toolkit Suspended
							</span>
						)}
					</div>
					<div className="flex items-center gap-2">
						{toolkit.disabled ? (
							<button
								type="button"
								disabled={killswitchMutation.isPending}
								onClick={() => setKillswitchConfirming((c) => !c)}
								className="bg-primary/10 border-primary/40 text-primary hover:bg-primary/20 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
							>
								<ShieldCheck className="h-4 w-4" /> Restore Access
							</button>
						) : (
							<button
								type="button"
								disabled={killswitchMutation.isPending}
								onClick={() => setKillswitchConfirming((c) => !c)}
								className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors disabled:opacity-50 ${killswitchConfirming ? 'bg-danger/10 border-danger/40 text-danger' : 'bg-muted border-border text-muted-foreground hover:text-danger hover:border-danger/40 hover:bg-danger/5'}`}
							>
								<Ban className="h-4 w-4" /> Kill switch
							</button>
						)}
						{!toolkit.disabled && (
							<button
								type="button"
								onClick={() => setShowKeyCreate(true)}
								className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
							>
								<Plus className="h-4 w-4" /> Create Key
							</button>
						)}
					</div>
				</div>
				{/* Kill switch confirmation row */}
				{killswitchConfirming && (
					<div
						className={`flex items-center gap-3 border-b px-5 py-3 ${toolkit.disabled ? 'border-danger/20 bg-danger/5' : 'border-border bg-background/40'}`}
					>
						<span className="text-muted-foreground flex-1 text-xs">
							{toolkit.disabled
								? 'Restore access to this toolkit?'
								: 'Block all API access for this toolkit immediately?'}
						</span>
						<button
							type="button"
							onClick={() => {
								killswitchMutation.mutate(!toolkit.disabled);
								setKillswitchConfirming(false);
							}}
							disabled={killswitchMutation.isPending}
							className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${toolkit.disabled ? 'bg-primary text-background hover:bg-primary/80' : 'bg-danger text-destructive-foreground hover:bg-danger/80'}`}
						>
							{toolkit.disabled ? 'Restore' : 'Kill Access'}
						</button>
						<button
							type="button"
							onClick={() => setKillswitchConfirming(false)}
							className="bg-muted border-border text-muted-foreground hover:bg-muted/60 rounded-lg border px-3 py-1.5 text-xs transition-colors"
						>
							Cancel
						</button>
					</div>
				)}
				<div className="space-y-3 px-5 py-4">
					{newKey && (
						<OneTimeKeyDisplay
							keyValue={newKey}
							onConfirm={() => setNewKey(null)}
							title="New API Key Created"
						/>
					)}
					{showKeyCreate && (
						<div className="bg-background border-border space-y-3 rounded-lg border p-4">
							<p className="text-foreground text-sm font-semibold">Create API Key</p>
							<input
								type="text"
								value={keyName}
								onChange={(e) => setKeyName(e.target.value)}
								placeholder="Key name (optional)"
								aria-label="Key name"
								className="bg-muted border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 text-sm focus:outline-hidden"
							/>
							<div className="flex gap-2">
								<button
									type="button"
									onClick={() =>
										createKeyMutation.mutate({ name: keyName || null })
									}
									disabled={createKeyMutation.isPending}
									className="bg-primary text-background hover:bg-primary/80 rounded-lg px-3 py-1.5 text-sm transition-colors disabled:opacity-50"
								>
									{createKeyMutation.isPending ? 'Generating...' : 'Generate'}
								</button>
								<button
									type="button"
									onClick={() => setShowKeyCreate(false)}
									className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-3 py-1.5 text-sm transition-colors"
								>
									Cancel
								</button>
							</div>
						</div>
					)}
					{keys.length === 0 && !showKeyCreate && !newKey && (
						<p className="text-muted-foreground text-sm">
							No keys yet. Create one to allow agents to use this toolkit.
						</p>
					)}
					{keys.map((key: any) => (
						<div
							key={key.id}
							className="bg-background flex items-center gap-3 rounded-lg p-3"
						>
							<Key className="text-accent-yellow h-4 w-4 shrink-0" />
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<span className="text-foreground text-sm font-medium">
										{key.label || 'Unnamed Key'}
									</span>
									{key.prefix && (
										<code className="text-muted-foreground font-mono text-xs">
											{key.prefix}...
										</code>
									)}
									{key.revoked_at && <Badge variant="danger">revoked</Badge>}
								</div>
								{key.created_at && (
									<p className="text-muted-foreground text-xs">
										{new Date(key.created_at * 1000).toLocaleString()}
									</p>
								)}
							</div>
							{!key.revoked_at && (
								<ConfirmInline
									onConfirm={() => revokeKeyMutation.mutate(key.id)}
									message="Revoke this key?"
									confirmLabel="Revoke"
								>
									<button
										type="button"
										className="bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 rounded border px-2 py-1 text-xs transition-colors"
									>
										Revoke
									</button>
								</ConfirmInline>
							)}
						</div>
					))}
				</div>
			</div>

			{/* Credentials */}
			<div className="bg-muted border-border overflow-hidden rounded-xl border">
				<div className="border-border flex items-center justify-between border-b px-5 py-4">
					<h3 className="font-heading text-foreground font-semibold">
						Bound Credentials ({credentials.length})
					</h3>
					<button
						type="button"
						onClick={() => navigate('/credentials')}
						className="bg-muted border-border text-foreground hover:bg-muted/60 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors"
					>
						<LinkIcon className="h-4 w-4" /> Manage Credentials
					</button>
				</div>
				<div className="space-y-2 px-5 py-4">
					{credentials.length === 0 ? (
						<p className="text-muted-foreground text-sm">
							No credentials bound. Bind credentials to grant this toolkit API access.
						</p>
					) : (
						credentials.map((cred: any) => (
							<div
								key={cred.credential_id}
								className="bg-background border-border overflow-hidden rounded-xl border"
							>
								<div className="flex items-center gap-3 px-4 py-3">
									<div className="min-w-0 flex-1">
										<span className="text-foreground text-sm font-medium">
											{cred.label}
										</span>
										{cred.api_id && (
											<p className="text-muted-foreground truncate font-mono text-xs">
												{cred.api_id}
											</p>
										)}
										{cred.permissions && (
											<p className="text-muted-foreground mt-0.5 text-xs">
												{
													cred.permissions.filter(
														(r: any) =>
															!r._comment?.includes('System safety'),
													).length
												}{' '}
												agent rule(s) + system safety
											</p>
										)}
									</div>
									<div className="flex shrink-0 items-center gap-1.5">
										<button
											type="button"
											onClick={() =>
												setEditingPermForCred(
													editingPermForCred === cred.credential_id
														? null
														: cred.credential_id,
												)
											}
											className="bg-muted border-border text-muted-foreground hover:text-foreground inline-flex items-center gap-1 rounded border px-2 py-1 text-xs transition-colors"
										>
											<Edit2 className="h-3 w-3" /> Permissions
											{editingPermForCred === cred.credential_id ? (
												<ChevronUp className="h-3 w-3" />
											) : (
												<ChevronDown className="h-3 w-3" />
											)}
										</button>
										{id !== 'default' && (
											<ConfirmInline
												onConfirm={() =>
													unbindMutation.mutate(cred.credential_id)
												}
												message="Unbind this credential?"
												confirmLabel="Unbind"
											>
												<button
													type="button"
													className="bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 inline-flex items-center gap-1 rounded border px-2 py-1 text-xs transition-colors"
												>
													<Unlink className="h-3 w-3" /> Unbind
												</button>
											</ConfirmInline>
										)}
									</div>
								</div>
								{editingPermForCred === cred.credential_id && (
									<CredentialPermissionEditor
										toolkitId={id!}
										credential={cred}
										onClose={() => setEditingPermForCred(null)}
									/>
								)}
							</div>
						))
					)}
				</div>
			</div>

			{/* Settings Modal */}
			{showSettings && (
				<div className="fixed inset-0 z-50 flex items-center justify-center p-4">
					<div
						className="absolute inset-0 bg-black/60 backdrop-blur-sm"
						onClick={() => setShowSettings(false)}
					/>
					<div className="bg-muted border-border relative z-10 w-full max-w-md space-y-5 rounded-xl border p-6">
						<div className="flex items-center justify-between">
							<h2 className="font-heading text-foreground text-lg font-semibold">
								Toolkit Settings
							</h2>
							<button
								type="button"
								onClick={() => setShowSettings(false)}
								className="text-muted-foreground hover:text-foreground"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
						<div className="space-y-4">
							<div>
								<label
									htmlFor="tk-settings-name"
									className="text-muted-foreground mb-1 block text-xs"
								>
									Name
								</label>
								<input
									id="tk-settings-name"
									type="text"
									value={editName}
									onChange={(e) => setEditName(e.target.value)}
									className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
								/>
							</div>
							<div>
								<label
									htmlFor="tk-settings-description"
									className="text-muted-foreground mb-1 block text-xs"
								>
									Description
								</label>
								<textarea
									id="tk-settings-description"
									value={editDesc}
									onChange={(e) => setEditDesc(e.target.value)}
									rows={2}
									className="bg-background border-border text-foreground focus:border-primary w-full resize-none rounded-lg border px-3 py-2 focus:outline-hidden"
								/>
							</div>
							<div className="flex gap-2">
								<button
									type="button"
									onClick={() => updateMutation.mutate()}
									disabled={updateMutation.isPending}
									className="bg-primary text-background hover:bg-primary/80 flex-1 rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50"
								>
									{updateMutation.isPending ? 'Saving...' : 'Save Changes'}
								</button>
								<button
									type="button"
									onClick={() => setShowSettings(false)}
									className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-4 py-2 transition-colors"
								>
									Cancel
								</button>
							</div>
							<div className="border-border border-t pt-4">
								<p className="text-muted-foreground mb-3 text-xs">Danger Zone</p>
								<ConfirmInline
									onConfirm={() => deleteMutation.mutate()}
									message="Permanently delete this toolkit?"
									confirmLabel="Delete Forever"
								>
									<button
										type="button"
										className="bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 inline-flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm transition-colors"
									>
										<Trash2 className="h-4 w-4" /> Delete Toolkit
									</button>
								</ConfirmInline>
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Request Access Dialog */}
			{showRequestAccess && (
				<RequestAccessDialog toolkitId={id!} onClose={() => setShowRequestAccess(false)} />
			)}
		</div>
	);
}
