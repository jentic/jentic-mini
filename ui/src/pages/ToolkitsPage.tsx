import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Wrench, AlertTriangle, Key, X, Ban } from 'lucide-react';
import { api } from '@/api/client';
import { usePendingRequests } from '@/hooks/usePendingRequests';
import type { ToolkitCreate } from '@/api/types';

function CreateModal({
	onClose,
	onCreated,
}: {
	onClose: () => void;
	onCreated: (id: string) => void;
}) {
	const queryClient = useQueryClient();
	const [name, setName] = useState('');
	const [description, setDescription] = useState('');
	const [simulate, setSimulate] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const mutation = useMutation({
		mutationFn: (data: ToolkitCreate) => api.createToolkit(data),
		onSuccess: (t) => {
			queryClient.invalidateQueries({ queryKey: ['toolkits'] });
			onCreated(t.id);
		},
		onError: (e: Error) => setError(e.message),
	});

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center p-4">
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
			<div className="bg-muted border-border relative z-10 w-full max-w-md space-y-5 rounded-xl border p-6">
				<div className="flex items-center justify-between">
					<h2 className="font-heading text-foreground text-lg font-semibold">
						Create Toolkit
					</h2>
					<button
						type="button"
						aria-label="Close"
						onClick={onClose}
						className="text-muted-foreground hover:text-foreground"
					>
						<X className="h-5 w-5" />
					</button>
				</div>
				<form
					onSubmit={(e) => {
						e.preventDefault();
						setError(null);
						mutation.mutate({ name, description: description || null, simulate });
					}}
					className="space-y-4"
				>
					<div>
						<label
							htmlFor="tk-create-name"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Name *
						</label>
						<input
							id="tk-create-name"
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							required
							autoFocus
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 focus:outline-hidden"
						/>
					</div>
					<div>
						<label
							htmlFor="tk-create-description"
							className="text-muted-foreground mb-1 block text-xs"
						>
							Description
						</label>
						<textarea
							id="tk-create-description"
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							rows={2}
							className="bg-background border-border text-foreground focus:border-primary w-full resize-none rounded-lg border px-3 py-2 focus:outline-hidden"
						/>
					</div>
					<label className="flex cursor-pointer items-center gap-3">
						<input
							type="checkbox"
							checked={simulate}
							onChange={(e) => setSimulate(e.target.checked)}
							className="rounded"
						/>
						<div>
							<span className="text-foreground text-sm">Simulate mode</span>
							<p className="text-muted-foreground text-xs">
								Returns mock responses without calling real APIs
							</p>
						</div>
					</label>
					{error && <p className="text-danger text-sm">{error}</p>}
					<div className="flex gap-2">
						<button
							type="submit"
							disabled={mutation.isPending}
							className="bg-primary text-background hover:bg-primary/80 flex-1 rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50"
						>
							{mutation.isPending ? 'Creating...' : 'Create Toolkit'}
						</button>
						<button
							type="button"
							onClick={onClose}
							className="bg-muted border-border text-foreground hover:bg-muted/60 rounded-lg border px-4 py-2 transition-colors"
						>
							Cancel
						</button>
					</div>
				</form>
			</div>
		</div>
	);
}

interface ToolkitsPageProps {
	createNew?: boolean;
}

export default function ToolkitsPage({ createNew = false }: ToolkitsPageProps) {
	const navigate = useNavigate();
	const [showCreate, setShowCreate] = useState(createNew);

	const { data: toolkits, isLoading } = useQuery({
		queryKey: ['toolkits'],
		queryFn: api.listToolkits,
		refetchInterval: 30000,
	});

	// Pending requests: fetched globally, grouped by toolkit_id here
	const { data: pendingRequests } = usePendingRequests();
	const pendingByToolkit = (pendingRequests ?? []).reduce<Record<string, number>>(
		(acc, req: any) => {
			if (req.toolkit_id) acc[req.toolkit_id] = (acc[req.toolkit_id] ?? 0) + 1;
			return acc;
		},
		{},
	);

	return (
		<div className="space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<p className="text-primary/60 font-mono text-[10px] tracking-widest uppercase">
						Management
					</p>
					<h1 className="font-heading text-foreground mt-1 text-2xl font-bold">
						Toolkits
					</h1>
				</div>
				<button
					type="button"
					onClick={() => setShowCreate(true)}
					className="bg-primary text-background hover:bg-primary/80 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
				>
					<Plus className="h-4 w-4" /> Create Toolkit
				</button>
			</div>

			{isLoading ? (
				<div className="text-muted-foreground py-16 text-center">Loading toolkits...</div>
			) : !toolkits || toolkits.length === 0 ? (
				<div className="text-muted-foreground bg-muted border-border rounded-xl border border-dashed p-12 text-center">
					<Wrench className="mx-auto mb-3 h-10 w-10 opacity-30" />
					<p className="text-foreground mb-1 font-medium">No toolkits yet</p>
					<p className="mb-4 text-sm">
						Create a toolkit to give an agent scoped access to your APIs.
					</p>
					<button
						type="button"
						onClick={() => setShowCreate(true)}
						className="bg-primary text-background hover:bg-primary/80 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
					>
						Create your first toolkit
					</button>
				</div>
			) : (
				<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
					{toolkits.map((toolkit) => {
						const pendingCount = pendingByToolkit[toolkit.id] ?? 0;
						return (
							<Link
								to={`/toolkits/${toolkit.id}`}
								key={toolkit.id}
								className={`bg-muted hover:border-primary/50 hover:bg-muted/80 block space-y-3 rounded-xl border p-5 transition-all ${toolkit.disabled ? 'border-danger/40 opacity-70' : 'border-border'}`}
							>
								<div className="flex items-start justify-between gap-2">
									<div>
										<div className="flex flex-wrap items-center gap-2">
											<h2 className="font-heading text-foreground font-semibold">
												{toolkit.name}
											</h2>
											{toolkit.disabled && (
												<span className="bg-danger/10 text-danger border-danger/30 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs">
													<Ban className="h-3 w-3" />
													SUSPENDED
												</span>
											)}
											{pendingCount > 0 && (
												<span className="bg-warning/10 text-warning border-warning/20 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs">
													<AlertTriangle className="h-3 w-3" />
													{pendingCount} pending
												</span>
											)}
											{toolkit.simulate && (
												<span className="bg-primary/10 text-primary border-primary/20 rounded-full border px-2 py-0.5 font-mono text-[10px]">
													simulate
												</span>
											)}
										</div>
										{toolkit.description && (
											<p className="text-muted-foreground mt-0.5 text-xs">
												{toolkit.description}
											</p>
										)}
									</div>
									<Wrench className="text-accent-teal mt-0.5 h-4 w-4 shrink-0" />
								</div>
								<div className="text-muted-foreground flex items-center gap-4 text-xs">
									<span className="flex items-center gap-1">
										<Key className="h-3 w-3" />
										{toolkit.key_count ?? '—'} keys
									</span>
									<span>
										{toolkit.credential_count != null
											? `${toolkit.credential_count} credentials`
											: toolkit.credentials?.length != null
												? `${toolkit.credentials.length} credentials`
												: '—'}
									</span>
								</div>
							</Link>
						);
					})}
				</div>
			)}

			{showCreate && (
				<CreateModal
					onClose={() => {
						setShowCreate(false);
						if (createNew) navigate('/toolkits');
					}}
					onCreated={(id) => {
						setShowCreate(false);
						navigate(`/toolkits/${id}`);
					}}
				/>
			)}
		</div>
	);
}
