import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { AlertTriangle, Check } from 'lucide-react';
import { UserService } from '@/api/generated';

/**
 * Setup wizard with two steps:
 *   1. Create admin account
 *   2. Generate agent API key (manual) — OR wait for agent to claim it
 *
 * The `step` state drives which panel is visible.  Health polling only
 * runs during step 2 (waiting-for-agent path) so it cannot interfere
 * with the key display.
 */
type Step = 'account' | 'key';

export default function SetupPage() {
	const [step, setStep] = useState<Step>('account');
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [copiedKey, setCopiedKey] = useState(false);

	// ── Step 2: Generate key (declared early so polling can reference it) ──
	const generateKeyMutation = useMutation({
		mutationFn: async () => {
			const r = await fetch('/default-api-key/generate', {
				method: 'POST',
				credentials: 'include',
			});
			if (!r.ok) throw new Error(`Key generation failed (${r.status})`);
			return r.json();
		},
	});

	// Health query — only polls during the key step (waiting for agent)
	const { data: health } = useQuery({
		queryKey: ['health'],
		queryFn: () => fetch('/health', { credentials: 'include' }).then((r) => r.json()),
		refetchInterval: (query) => {
			// Only poll while waiting for an agent to claim the key.
			// Stop polling if the user is generating the key manually.
			if (step !== 'key') return false;
			if (generateKeyMutation.data || generateKeyMutation.isPending) return false;
			const status = query.state.data?.status;
			return status === 'setup_required' ? 3000 : false;
		},
	});

	// If health shows everything is already set up AND the user hasn't
	// started the wizard yet, skip straight to the done screen.
	// Once the user has progressed past account creation we trust the
	// step state so health polling can't yank the UI away.
	const alreadySetUp = step === 'account' && health?.status === 'ok';

	// If the account already exists but the key hasn't been claimed yet
	// (e.g. page refresh after account creation), advance to the key step.
	useEffect(() => {
		if (step === 'account' && health?.account_created && health?.status !== 'ok') {
			setStep('key');
		}
	}, [step, health?.account_created, health?.status]);

	// ── Step 1: Create account ──────────────────────────────────────────
	const createUserMutation = useMutation({
		mutationFn: () =>
			UserService.createUserUserCreatePost({ requestBody: { username, password } }),
		onSuccess: () => {
			fetch('/user/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ username, password }),
			})
				.then((res) => {
					if (!res.ok)
						console.warn('Auto-login failed after account creation:', res.status);
					// Advance to key step regardless — account exists, login can be retried
					setStep('key');
				})
				.catch(() => {
					// Network error — still advance to key step
					setStep('key');
				});
		},
	});

	const createUserError = createUserMutation.error as { status?: number } | null;
	const accountAlreadyExists = createUserError?.status === 409 || createUserError?.status === 410;

	// Agent claimed the key externally (detected via polling).
	// Guard on health being defined to avoid a flash on initial mount.
	const agentClaimedKey =
		step === 'key' &&
		health != null &&
		health.status !== 'setup_required' &&
		!generateKeyMutation.data;

	return (
		<div className="bg-background text-foreground flex min-h-screen items-center justify-center">
			<div className="bg-muted border-border w-full max-w-md rounded-xl border p-8 shadow-2xl">
				<h1 className="text-foreground mb-6 text-center text-3xl font-bold">
					Welcome to Jentic Mini
				</h1>

				{/* ── Already set up ── */}
				{alreadySetUp ? (
					<div className="text-center">
						<div className="bg-success/10 border-success/30 text-success mb-6 flex items-center justify-center gap-2 rounded-lg border p-4 text-sm font-semibold">
							<Check className="h-4 w-4" /> Setup complete
						</div>
						<button
							type="button"
							onClick={() => (window.location.href = '/')}
							className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-bold transition-colors"
						>
							Go to Dashboard →
						</button>
					</div>
				) : null}

				{/* ── Step 1: Create admin account ── */}
				{!alreadySetUp && step === 'account' ? (
					<form
						onSubmit={(e) => {
							e.preventDefault();
							createUserMutation.mutate();
						}}
					>
						<h2 className="text-foreground mb-4 text-xl font-semibold">
							Create Admin Account
						</h2>

						{accountAlreadyExists && (
							<div
								role="alert"
								className="bg-warning/10 border-warning/30 text-warning mb-4 rounded-lg border p-3 text-sm"
							>
								An admin account already exists.{' '}
								<a href="/login" className="font-semibold underline">
									Log in instead →
								</a>
							</div>
						)}

						{createUserMutation.isError && !accountAlreadyExists && (
							<div
								role="alert"
								className="bg-danger/10 border-danger/30 text-danger mb-4 rounded-lg border p-3 text-sm"
							>
								Something went wrong. Please try again.
							</div>
						)}

						<div className="mb-4">
							<label
								htmlFor="setup-username"
								className="text-muted-foreground mb-2 block text-sm font-bold"
							>
								Username
							</label>
							<input
								id="setup-username"
								type="text"
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								required
								disabled={accountAlreadyExists}
								className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 transition-colors focus:outline-hidden disabled:opacity-50"
							/>
						</div>
						<div className="mb-6">
							<label
								htmlFor="setup-password"
								className="text-muted-foreground mb-2 block text-sm font-bold"
							>
								Password
							</label>
							<input
								id="setup-password"
								type="password"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
								disabled={accountAlreadyExists}
								className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 transition-colors focus:outline-hidden disabled:opacity-50"
							/>
						</div>
						{!accountAlreadyExists && (
							<button
								type="submit"
								disabled={createUserMutation.isPending}
								className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-bold transition-colors disabled:opacity-50"
							>
								{createUserMutation.isPending ? 'Creating...' : 'Create Account'}
							</button>
						)}
					</form>
				) : null}

				{/* ── Step 2: Agent key ── */}
				{!alreadySetUp && step === 'key' ? (
					<div>
						<div className="bg-success/10 border-success/30 text-success mb-6 flex items-center justify-center gap-2 rounded-lg border p-4 text-center text-sm font-semibold">
							<Check className="h-4 w-4" /> Admin account created
						</div>

						{/* Key generated — show it until copied */}
						{generateKeyMutation.data && !copiedKey ? (
							<div className="bg-danger/10 border-danger/30 mb-4 rounded-lg border p-4">
								<div className="text-danger mb-2 flex items-center gap-2 text-sm font-bold">
									<AlertTriangle className="h-4 w-4 shrink-0" /> This key will not
									be shown again
								</div>
								<div className="bg-background text-foreground mb-4 rounded p-3 font-mono text-sm break-all">
									{generateKeyMutation.data.key}
								</div>
								<button
									type="button"
									onClick={async () => {
										try {
											await navigator.clipboard.writeText(
												generateKeyMutation.data.key,
											);
											setCopiedKey(true);
										} catch {
											window.alert(
												'Could not copy to clipboard. Please copy the key manually.',
											);
										}
									}}
									className="bg-primary text-background hover:bg-primary-hover w-full rounded py-2 font-semibold transition-colors"
								>
									Copy Key
								</button>
							</div>
						) : /* Key copied — show confirmation + proceed */
						copiedKey ? (
							<div className="text-center">
								<div className="bg-success/10 border-success/30 text-success mb-6 flex items-center justify-center gap-2 rounded-lg border p-4 text-sm font-semibold">
									<Check className="h-4 w-4" /> API key copied
								</div>
								<button
									type="button"
									onClick={() => (window.location.href = '/')}
									className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-bold transition-colors"
								>
									Go to Dashboard →
								</button>
							</div>
						) : /* Agent claimed key externally */
						agentClaimedKey ? (
							<div className="text-center">
								<div className="bg-success/10 border-success/30 text-success mb-6 flex items-center justify-center gap-2 rounded-lg border p-4 text-sm font-semibold">
									<Check className="h-4 w-4" /> Agent claimed the key
									automatically
								</div>
								<button
									type="button"
									onClick={() => (window.location.href = '/')}
									className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-bold transition-colors"
								>
									Go to Dashboard →
								</button>
							</div>
						) : (
							/* Initial state — generate or wait */
							<>
								<p className="text-muted-foreground mb-4 text-sm">
									Your AI agent can claim this key automatically. To set it up:
								</p>
								<ol className="text-muted-foreground mb-4 list-inside list-decimal space-y-1 text-sm">
									<li>
										Install the Jentic skill:{' '}
										<code className="bg-background rounded px-1 font-mono">
											clawhub install jentic
										</code>
									</li>
									<li>Tell your agent the URL of this Jentic Mini instance</li>
									<li>
										Your agent will discover and claim the key automatically
									</li>
								</ol>
								<p className="text-muted-foreground mb-4 text-sm">
									Alternatively, generate the API key now and give it to your
									agent manually.
								</p>
								<button
									type="button"
									onClick={() => generateKeyMutation.mutate()}
									disabled={generateKeyMutation.isPending}
									className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-semibold transition-colors disabled:opacity-50"
								>
									{generateKeyMutation.isPending
										? 'Generating...'
										: 'Generate Agent API Key'}
								</button>
							</>
						)}
					</div>
				) : null}
			</div>
		</div>
	);
}
