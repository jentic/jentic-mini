import { useQuery } from '@tanstack/react-query';
import { useAuth } from './useAuth';
import { api } from '@/api/client';

export function usePendingRequests() {
	const { user } = useAuth();

	return useQuery({
		queryKey: ['pending_requests'],
		queryFn: async () => {
			const toolkits = await api.listToolkits();
			const results: Array<Record<string, unknown> & { toolkit_name: string }> = [];
			for (const t of toolkits) {
				try {
					const reqs = await api.listAccessRequests(t.id, 'pending');
					if (Array.isArray(reqs)) {
						for (const r of reqs) {
							if (r.status === 'pending') {
								results.push({ ...r, toolkit_name: t.name });
							}
						}
					}
				} catch {
					// ignore per-toolkit errors
				}
			}
			return results;
		},
		enabled: !!user?.logged_in,
		refetchInterval: 30000,
	});
}
