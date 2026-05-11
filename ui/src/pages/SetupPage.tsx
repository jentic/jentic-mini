import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AppLink } from '@/components/ui/AppLink';
import { UserService } from '@/api/generated';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { apiUrl } from '@/api/client';

type HealthPayload = {
	status: string;
	account_created?: boolean;
};

/**
 * First-time setup: create the admin account. Agent onboarding is handled after login.
 */
export default function SetupPage() {
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');

	const { data: health } = useQuery({
		queryKey: ['health'],
		queryFn: () =>
			fetch(apiUrl('/health'), { credentials: 'include' }).then((r) =>
				r.json(),
			) as Promise<HealthPayload>,
	});

	// POST /user/create auto-issues the session cookie on success, so a
	// separate /user/login call is unnecessary. We deliberately do NOT
	// invalidate ['health'] / ['user', 'me'] in onSuccess — doing so causes
	// AuthGuard to redirect away from /setup the instant both queries refetch,
	// before "Setup complete" can render. The invalidations happen on the
	// "Go to Dashboard" click so the user sees the success screen first.
	const createUserMutation = useMutation({
		mutationFn: async () => {
			await UserService.createUserUserCreatePost({
				requestBody: { username, password },
			});
		},
	});

	const createUserError = createUserMutation.error as {
		status?: number;
		message?: string;
	} | null;
	const accountAlreadyExists = createUserError?.status === 409 || createUserError?.status === 410;

	const alreadySetUp = health?.status === 'ok' || createUserMutation.isSuccess;

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
						<Button
							onClick={() => {
								// Invalidate auth queries so AuthGuard sees the new
								// session, then navigate. Doing this here (rather
								// than in onSuccess) lets "Setup complete" actually
								// render before AuthGuard would otherwise redirect.
								void queryClient.invalidateQueries({ queryKey: ['health'] });
								void queryClient.invalidateQueries({ queryKey: ['user', 'me'] });
								navigate('/', { replace: true });
							}}
							size="lg"
							fullWidth
						>
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

				<div className="border-border bg-background/50 mb-6 rounded-lg border p-4 text-sm">
					<p className="text-muted-foreground leading-relaxed">
						Create your administrator account below. Agents register themselves
						afterward; you&apos;ll approve them from the dashboard once you&apos;re
						signed in.
					</p>
				</div>

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
							message={
								createUserError?.message ??
								'Something went wrong. Please try again.'
							}
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
