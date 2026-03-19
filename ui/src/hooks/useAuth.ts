import { useQuery } from '@tanstack/react-query'
import { UserService } from '../api/generated'

export function useAuth() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['user', 'me'],
    queryFn: () => UserService.meUserMeGet(),
    retry: false
  })

  // We check health status for "account_required"
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health').then(r => r.json()),
    retry: false
  })

  const isAccountRequired = healthQuery.data?.status === 'account_required'

  return {
    user: data,
    isLoading: isLoading || healthQuery.isLoading,
    error,
    isAccountRequired,
    refetch
  }
}
