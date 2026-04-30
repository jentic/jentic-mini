import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check } from 'lucide-react';
import { AppLink } from '@/components/ui/AppLink';
import { UserService } from '@/api/generated';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

type HealthPayload = {
	status: string;
	account_created?: boolean;
	oauth_authorization_server_metadata?: string;
	registration_endpoint?: string;
	token_endpoint?: string;
	setup_url?: string;
	next_step?: string;
};

/**
 * First-time setup: create the admin account. Agents onboard separately via OAuth DCR
 * (URLs are returned on GET /health while setup_required).
 */
export default function SetupPage() {
	const queryClient = useQueryClient();
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');

	const { data: health } = useQuery({
		queryKey: ['health'],
		queryFn: () =>
			fetch('/health', { credentials: 'include' }).then((r) =>
				r.json(),
			) as Promise<HealthPayload>,
	});

	const createUserMutation = useMutation({
		mutationFn: () =>
			UserService.createUserUserCreatePost({ requestBody: { username, password } }),
		onSuccess: () => {
			fetch('/user/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ username, password }),
			}).finally(() => {
				void queryClient.invalidateQueries({ queryKey: ['health'] });
				void queryClient.invalidateQueries({ queryKey: ['user', 'me'] });
			});
		},
	});

	const createUserError = createUserMutation.error as { status?: number } | null;
	const accountAlreadyExists = createUserError?.status === 409 || createUserError?.status === 410;

	const alreadySetUp = health?.status === 'ok';

	if (alreadySetUp) {
		return (
			<div className="bg-background text-foreground flex min-h-screen items-center justify-center">
				<div className="bg-muted border-border w-full max-w-md rounded-xl border p-8 shadow-2xl">
					<h1 className="text-foreground mb-6 text-center text-3xl font-bold">
						Welcome to Jentic Mini
					</h1>
					<div className="text-center">
						<div className="bg-success/10 border-success/30 text-success mb-6 flex items-center justify-center gap-2 rounded-lg border p-4 text-sm font-semibold">
							<Check className="h-4 w-4" /> Setup complete
						</div>
						<Button onClick={() => (window.location.href = '/')} size="lg" fullWidth>
							Go to Dashboard →
						</Button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="bg-background text-foreground flex min-h-screen items-center justify-center">
			<div className="bg-muted border-border w-full max-w-lg rounded-xl border p-8 shadow-2xl">
				<h1 className="text-foreground mb-6 text-center text-3xl font-bold">
					Welcome to Jentic Mini
				</h1>

				{health?.oauth_authorization_server_metadata && (
					<div className="border-border bg-background/50 mb-6 rounded-lg border p-4 text-sm">
						<p className="text-muted-foreground mb-2 font-semibold">
							For agents (OAuth)
						</p>
						<ul className="text-muted-foreground space-y-1 font-mono text-xs break-all">
							<li>Metadata: {health.oauth_authorization_server_metadata}</li>
							{health.registration_endpoint && (
								<li>Register: {health.registration_endpoint}</li>
							)}
							{health.token_endpoint && <li>Token: {health.token_endpoint}</li>}
						</ul>
						<p className="text-muted-foreground mt-2 text-xs">{health.next_step}</p>
					</div>
				)}

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
							<AppLink href="/login" className="font-semibold underline">
								Log in instead →
							</AppLink>
						</div>
					)}

					{createUserMutation.isError && !accountAlreadyExists && (
						<ErrorAlert
							message="Something went wrong. Please try again."
							className="mb-4"
						/>
					)}

					<div className="mb-4">
						<Label
							htmlFor="setup-username"
							className="text-muted-foreground mb-2 block font-bold"
							required
						>
							Username
						</Label>
						<Input
							id="setup-username"
							type="text"
							value={username}
							onChange={(e) => setUsername(e.target.value)}
							required
							disabled={accountAlreadyExists}
							className="bg-background"
						/>
					</div>
					<div className="mb-6">
						<Label
							htmlFor="setup-password"
							className="text-muted-foreground mb-2 block font-bold"
							required
						>
							Password
						</Label>
						<Input
							id="setup-password"
							type="password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
							disabled={accountAlreadyExists}
							showPasswordToggle
							className="bg-background"
						/>
					</div>
					{!accountAlreadyExists && (
						<Button
							type="submit"
							loading={createUserMutation.isPending}
							size="lg"
							fullWidth
						>
							{createUserMutation.isPending ? 'Creating...' : 'Create Account'}
						</Button>
					)}
				</form>
			</div>
		</div>
	);
}
