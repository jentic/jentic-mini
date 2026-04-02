import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { JenticLogo } from '@/components/ui/Logo';

export default function LoginPage() {
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [searchParams] = useSearchParams();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const next = searchParams.get('next') || '/';

	const loginMutation = useMutation({
		mutationFn: async () => {
			const res = await fetch('/user/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ username, password }),
			});
			if (!res.ok) throw new Error('Login failed');
			return res.json();
		},
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ['user', 'me'] });
			navigate(next, { replace: true });
		},
	});

	return (
		<div className="bg-background text-foreground flex min-h-screen items-center justify-center">
			<div className="bg-muted border-border w-full max-w-sm rounded-xl border p-8 shadow-2xl">
				<div className="mb-8 flex justify-center">
					<JenticLogo className="h-12" />
				</div>

				<form
					onSubmit={(e) => {
						e.preventDefault();
						loginMutation.mutate();
					}}
				>
					{loginMutation.isError && (
						<div
							role="alert"
							className="bg-danger/10 text-danger border-danger/30 mb-4 rounded-lg border p-3 text-sm font-semibold"
						>
							Invalid username or password.
						</div>
					)}

					<div className="mb-4">
						<label
							htmlFor="login-username"
							className="text-muted-foreground mb-2 block text-sm font-bold"
						>
							Username
						</label>
						<input
							id="login-username"
							type="text"
							value={username}
							onChange={(e) => setUsername(e.target.value)}
							required
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 transition-colors focus:outline-hidden"
						/>
					</div>

					<div className="mb-8">
						<label
							htmlFor="login-password"
							className="text-muted-foreground mb-2 block text-sm font-bold"
						>
							Password
						</label>
						<input
							id="login-password"
							type="password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
							className="bg-background border-border text-foreground focus:border-primary w-full rounded-lg border px-3 py-2 transition-colors focus:outline-hidden"
						/>
					</div>

					<button
						type="submit"
						disabled={loginMutation.isPending}
						className="bg-primary text-background hover:bg-primary-hover w-full rounded-lg px-4 py-3 font-bold transition-colors disabled:opacity-50"
					>
						{loginMutation.isPending ? 'Logging in...' : 'Log In'}
					</button>
				</form>

				<p className="text-muted-foreground mt-6 text-center text-xs">
					To reset your password, run{' '}
					<code className="bg-background px-1 font-mono">
						docker exec jentic-mini python3 -m jentic reset-password
					</code>
					.
				</p>
			</div>
		</div>
	);
}
