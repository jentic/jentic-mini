import { useQuery } from '@tanstack/react-query';
import { UserService } from '@/api/generated';

export function useAuth() {
	// Check system setup state first
	const healthQuery = useQuery({
		queryKey: ['health'],
		queryFn: () => fetch('/health').then((r) => r.json()),
		retry: false,
	});

	const isSetupComplete = healthQuery.data?.status === 'ok';
	const isSetupOrAccountRequired =
		healthQuery.data?.status === 'account_required' ||
		healthQuery.data?.status === 'setup_required';

	// Only check user session if setup is complete
	const { data, isLoading, error, refetch } = useQuery({
		queryKey: ['user', 'me'],
		queryFn: () => UserService.meUserMeGet(),
		retry: false,
		enabled: isSetupComplete, // ← Only run after setup
	});

	return {
		user: data,
		isLoading: isLoading || healthQuery.isLoading,
		error,
		isSetupOrAccountRequired,
		refetch,
	};
}
