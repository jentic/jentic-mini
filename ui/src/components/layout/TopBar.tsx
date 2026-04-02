import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Bell, LogOut, User, ChevronDown } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { JenticLogo } from '@/components/ui/Logo';
import { api } from '@/api/client';

interface TopBarProps {
	username?: string;
	pendingCount?: number;
}

export function TopBar({ username, pendingCount = 0 }: TopBarProps) {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const [search, setSearch] = useState('');
	const [userMenuOpen, setUserMenuOpen] = useState(false);

	const logoutMutation = useMutation({
		mutationFn: api.logout,
		onSuccess: () => {
			queryClient.clear();
			navigate('/login');
		},
	});

	const handleSearch = (e: React.FormEvent) => {
		e.preventDefault();
		if (search.trim()) {
			navigate(`/search?q=${encodeURIComponent(search.trim())}`);
			setSearch('');
		}
	};

	return (
		<header className="bg-background border-border sticky top-0 z-40 flex h-14 items-center gap-4 border-b px-4">
			{/* Logo */}
			<a href="/" className="shrink-0">
				<JenticLogo />
			</a>

			{/* Search */}
			<form onSubmit={handleSearch} className="max-w-md flex-1">
				<div className="relative">
					<Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
					<input
						type="text"
						placeholder="Search catalog..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="bg-muted border-border text-foreground placeholder:text-muted-foreground focus:border-primary w-full rounded-lg border py-1.5 pr-4 pl-9 text-sm transition-all focus:outline-hidden"
					/>
				</div>
			</form>

			<div className="flex-1" />

			{/* Pending requests badge */}
			{pendingCount > 0 && (
				<button
					type="button"
					onClick={() => navigate('/toolkits')}
					className="text-warning hover:text-warning/80 relative flex items-center gap-1.5 text-sm transition-colors"
					title={`${pendingCount} pending access request${pendingCount !== 1 ? 's' : ''}`}
				>
					<Bell className="h-4 w-4" />
					<span className="bg-danger text-background absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold">
						{pendingCount > 9 ? '9+' : pendingCount}
					</span>
				</button>
			)}

			{/* User menu */}
			<div className="relative">
				<button
					type="button"
					onClick={() => setUserMenuOpen(!userMenuOpen)}
					className="text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm transition-colors"
				>
					<User className="h-4 w-4" />
					<span>{username || 'Admin'}</span>
					<ChevronDown className="h-3 w-3" />
				</button>

				{userMenuOpen && (
					<>
						<div
							className="fixed inset-0 z-10"
							onClick={() => setUserMenuOpen(false)}
						/>
						<div className="bg-muted border-border absolute top-full right-0 z-20 mt-1 w-40 rounded-lg border py-1 shadow-xl">
							<button
								type="button"
								onClick={() => {
									setUserMenuOpen(false);
									logoutMutation.mutate();
								}}
								className="text-muted-foreground hover:text-foreground hover:bg-background/50 flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors"
							>
								<LogOut className="h-4 w-4" />
								Log out
							</button>
						</div>
					</>
				)}
			</div>
		</header>
	);
}
