import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Trash2, Settings } from 'lucide-react';
import { api } from '@/api/client';
import type { CredentialOut } from '@/api/types';
import { Badge } from '@/components/ui/Badge';
import { ConfirmInline } from '@/components/ui/ConfirmInline';

export default function CredentialsPage() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	const { data: credentialsRaw, isLoading } = useQuery({
		queryKey: ['credentials'],
		queryFn: () => api.listCredentials(),
	});
	const credentials =
		(credentialsRaw as any)?.data ?? (credentialsRaw as CredentialOut[] | undefined) ?? [];

	const deleteMutation = useMutation({
		mutationFn: (id: string) => api.deleteCredential(id),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
	});

	return (
		<div className="max-w-5xl space-y-5">
			<div className="flex items-center justify-between">
				<div>
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Management
					</p>
					<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
						Credentials Vault
					</h1>
				</div>
				<button
					type="button"
					onClick={() => navigate('/credentials/new')}
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
				>
					<Plus className="h-4 w-4" /> Add Credential
				</button>
			</div>

			<div className="bg-muted border-border text-muted-foreground rounded-xl border p-4 text-sm">
				Store API credentials securely. Bind them to toolkits to give agents scoped access
				to external APIs. Values are write-only — they are never returned by the API.
			</div>

			{isLoading ? (
				<div className="text-muted-foreground py-16 text-center">
					Loading credentials...
				</div>
			) : !credentials || credentials.length === 0 ? (
				<div className="text-muted-foreground bg-muted border-border rounded-xl border border-dashed p-12 text-center">
					<Key className="mx-auto mb-3 h-10 w-10 opacity-30" />
					<p className="text-foreground mb-1 font-medium">No credentials stored</p>
					<p className="mb-4 text-sm">
						Add a credential to authenticate agents with external APIs.
					</p>
					<button
						type="button"
						onClick={() => navigate('/credentials/new')}
						className="bg-primary text-background hover:bg-primary/80 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
					>
						Add your first credential
					</button>
				</div>
			) : (
				<div className="space-y-2">
					{(credentials as CredentialOut[]).map((cred) => (
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
								<button
									type="button"
									onClick={() =>
										navigate(`/credentials/${encodeURIComponent(cred.id)}/edit`)
									}
									className="bg-muted border-border text-foreground hover:bg-muted/60 inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm transition-colors"
								>
									<Settings className="h-4 w-4" /> Edit
								</button>
								<ConfirmInline
									onConfirm={() => deleteMutation.mutate(cred.id)}
									message="Delete this credential?"
									confirmLabel="Delete"
								>
									<button
										type="button"
										className="bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm transition-colors"
									>
										<Trash2 className="h-4 w-4" />
									</button>
								</ConfirmInline>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
