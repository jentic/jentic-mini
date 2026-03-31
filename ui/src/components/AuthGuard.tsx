import { Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function AuthGuard() {
  const { user, isLoading, isSetupOrAccountRequired } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (isSetupOrAccountRequired) {
    if (location.pathname !== '/setup') return <Navigate to="/setup" replace />
    return <Outlet />
  }

  if (!user?.logged_in) {
    if (location.pathname !== '/login') {
      return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
    }
    return <Outlet />
  }

  if (location.pathname === '/login' || location.pathname === '/setup') {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
