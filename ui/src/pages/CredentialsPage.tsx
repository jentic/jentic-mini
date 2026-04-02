import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Trash2, Settings } from 'lucide-react';
import { api } from '@/api/client';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ConfirmInline } from '@/components/ui/ConfirmInline';
import { PageHeader } from '@/components/ui/PageHeader';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { useAuth } from '@/hooks/useAuth';

function formatSyncedAt(ts: number): string {
	return new Date(ts * 1000).toLocaleString();
}

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
		mutationFn: (id: string) => api.deleteCredential(id),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
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
			<div className="bg-muted border-border text-muted-foreground rounded-xl border p-4 text-sm">
				Store API credentials securely. Bind them to toolkits to give agents scoped access
				to external APIs. Values are write-only — they are never returned by the API.
			</div>
			{isLoading || !user?.logged_in ? (
				<LoadingState message="Loading credentials..." />
			) : isError ? (
				<ErrorAlert message="Failed to load credentials. Please try refreshing the page." />
			) : !credentials || credentials.length === 0 ? (
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
			) : (
				<div className="space-y-2">
					{credentials.map((cred: any) => (
						<div
							key={cred.id}
							className="bg-muted border-border flex items-center gap-3 rounded-xl border p-4"
						>
							<Key className="text-accent-yellow h-5 w-5 shrink-0" />
							<div className="min-w-0 flex-1">
								<div className="flex flex-wrap items-center gap-2">
									<span className="text-foreground font-medium">
										{cred.label}
									</span>
									{cred.app_slug && (
										<span className="text-muted-foreground text-xs">({cred.app_slug})</span>
									)}
									{cred.api_id && (
										<span className="text-muted-foreground font-mono text-xs">
											{cred.api_id}
										</span>
									)}
									{cred.auth_type === 'pipedream_oauth' ? (
										<Badge variant="default" className="text-[10px]">OAuth</Badge>
									) : cred.scheme_name ? (
										<Badge variant="default" className="text-[10px]">{cred.scheme_name}</Badge>
									) : null}
								</div>
								<p className="text-muted-foreground mt-0.5 text-xs">
									{cred.auth_type === 'pipedream_oauth' && cred.account_id ? (
										<>
											<span>account: {cred.account_id}</span>
											{cred.synced_at && (
												<span className="ml-2">synced {formatSyncedAt(cred.synced_at)}</span>
											)}
										</>
									) : cred.created_at ? (
										<span>Added {new Date(cred.created_at * 1000).toLocaleDateString()}</span>
									) : null}
								</p>
							</div>
							<div className="flex items-center gap-2">
								{cred.auth_type !== 'pipedream_oauth' && (
									<Button
										variant="secondary"
										size="sm"
										onClick={() =>
											navigate(`/credentials/${encodeURIComponent(cred.id)}/edit`)
										}
									>
										<Settings className="h-4 w-4" /> Edit
									</Button>
								)}
								<ConfirmInline
									onConfirm={() => deleteMutation.mutate(cred.id)}
									message="Delete this credential?"
									confirmLabel="Delete"
								>
									<Button variant="danger" size="sm">
										<Trash2 className="h-4 w-4" />
									</Button>
								</ConfirmInline>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}


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
		mutationFn: (id: string) => api.deleteCredential(id),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
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
			<div className="bg-muted border-border text-muted-foreground rounded-xl border p-4 text-sm">
				Store API credentials securely. Bind them to toolkits to give agents scoped access
				to external APIs. Values are write-only — they are never returned by the API.
			</div>
			{isLoading || !user?.logged_in ? (
				<LoadingState message="Loading credentials..." />
			) : isError ? (
				<ErrorAlert message="Failed to load credentials. Please try refreshing the page." />
			) : !credentials || credentials.length === 0 ? (
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
			) : (
				<div className="space-y-2">
					{credentials.map((cred: any) => (
						<div
							key={cred.id}
							className="bg-muted border-border flex items-center gap-3 rounded-xl border p-4"
						>
							<Key className="text-accent-yellow h-5 w-5 shrink-0" />
							<div className="min-w-0 flex-1">
								<div className="flex flex-wrap items-center gap-2">
									<span className="text-foreground font-medium">
										{cred.label}
									</span>
									{cred.api_id && (
										<span className="text-muted-foreground font-mono text-xs">
											{cred.api_id}
										</span>
									)}
									{cred.scheme_name && (
										<Badge variant="default" className="text-[10px]">
											{cred.scheme_name}
										</Badge>
									)}
								</div>
								{cred.created_at && (
									<p className="text-muted-foreground mt-0.5 text-xs">
										Added{' '}
										{new Date(cred.created_at * 1000).toLocaleDateString()}
									</p>
								)}
							</div>
							<div className="flex items-center gap-2">
								{cred.auth_type !== 'pipedream_oauth' && (
									<Button
										variant="secondary"
										size="sm"
										onClick={() =>
											navigate(`/credentials/${encodeURIComponent(cred.id)}/edit`)
										}
									>
										<Settings className="h-4 w-4" /> Edit
									</Button>
								)}
								<ConfirmInline
									onConfirm={() => deleteMutation.mutate(cred.id)}
									message="Delete this credential?"
									confirmLabel="Delete"
								>
									<Button variant="danger" size="sm">
										<Trash2 className="h-4 w-4" />
									</Button>
								</ConfirmInline>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
