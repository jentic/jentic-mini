import { Outlet, Link, useLocation } from 'react-router-dom'
import { JenticLogo } from '../ui/Logo'
import { BookOpen, ExternalLink } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { usePendingRequests } from '../../hooks/usePendingRequests'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { UserService } from '../../api/generated'

function NavLink({ to, icon, label, exact = false }: { to: string; icon: React.ReactNode; label: string; exact?: boolean }) {
  const loc = useLocation()
  const active = exact ? loc.pathname === to : loc.pathname.startsWith(to)
  return (
    <Link 
      to={to} 
      className={`flex items-center gap-3 px-4 py-2 my-1 rounded-md transition-all duration-150 ${
        active 
          ? 'bg-muted/80 text-primary border-l-2 border-primary' 
          : 'text-foreground hover:bg-muted hover:text-primary'
      }`}
    >
      {icon}
      <span className="font-semibold">{label}</span>
    </Link>
  )
}

export function Layout() {
  const { user } = useAuth()
  const { data: pendingRequests } = usePendingRequests()
  const queryClient = useQueryClient()

  const logoutMutation = useMutation({
    mutationFn: () => UserService.logoutUserLogoutPost(),
    onSuccess: () => {
      queryClient.clear()
      window.location.href = '/login'
    }
  })

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside className="w-60 bg-muted border-r border-border flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border">
          <JenticLogo />
        </div>
        
        <nav className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-1">
          <NavLink to="/" exact icon={<span>📊</span>} label="Dashboard" />
          <NavLink to="/search" icon={<span>🔍</span>} label="Search" />
          
          <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">Directory</div>
          <NavLink to="/catalog" icon={<span>📚</span>} label="API Catalog" />
          <NavLink to="/workflows" icon={<span>🌐</span>} label="Workflows" />
          
          <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">Security</div>
          <NavLink to="/toolkits" icon={<span>🛡️</span>} label="Toolkits" />
          <NavLink to="/credentials" icon={<span>🔐</span>} label="Credentials" />
          <NavLink to="/oauth-brokers" icon={<span>🔗</span>} label="OAuth Brokers" />
          
          <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">Observability</div>
          <NavLink to="/traces" icon={<span>📈</span>} label="Traces" />
          <NavLink to="/jobs" icon={<span>⚙️</span>} label="Async Jobs" />
        </nav>

        <div className="px-3 py-3 border-t border-border">
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-4 py-2 rounded-md text-sm text-foreground hover:bg-muted hover:text-primary transition-all duration-150"
            aria-label="API (opens in a new tab)"
            title="API (opens in a new tab)"
          >
            <BookOpen className="h-4 w-4" />
            <span className="font-semibold">API</span>
          </a>
          <a
            href="https://jentic.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 pt-2 text-[11px] font-medium text-muted-foreground/70 hover:text-primary transition-colors"
          >
            <ExternalLink className="h-3 w-3 shrink-0" />
            More at jentic.com
          </a>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col bg-background/50">
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-background/80 backdrop-blur">
          <div className="flex-1"></div>
          <div className="flex items-center gap-4">
            {pendingRequests && pendingRequests.length > 0 && (
              <Link 
                to="/toolkits" 
                className="bg-danger/10 text-danger border border-danger/30 rounded-full px-3 py-1 text-sm font-semibold flex items-center gap-2 hover:bg-danger/20 transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-danger animate-pulse"></span>
                {pendingRequests.length} Pending {pendingRequests.length === 1 ? 'Request' : 'Requests'}
              </Link>
            )}
            <div className="text-sm font-mono text-muted-foreground">{user?.username}</div>
            <button 
              onClick={() => logoutMutation.mutate()} 
              className="text-muted-foreground hover:text-primary transition-colors text-sm"
              title="Log out"
            >
              Logout
            </button>
          </div>
        </header>
        
        <div className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
