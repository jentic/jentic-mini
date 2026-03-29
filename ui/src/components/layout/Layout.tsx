import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { JenticLogo } from '../ui/Logo'
import { BookOpen, ExternalLink, Menu, X } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { usePendingRequests } from '../../hooks/usePendingRequests'
import { useUpdateCheck } from '../../hooks/useUpdateCheck'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { UserService } from '../../api/generated'

function NavLink({
  to,
  icon,
  label,
  exact = false,
  onClick,
}: {
  to: string
  icon: React.ReactNode
  label: string
  exact?: boolean
  onClick?: () => void
}) {
  const loc = useLocation()
  const active = exact ? loc.pathname === to : loc.pathname.startsWith(to)
  return (
    <Link
      to={to}
      onClick={onClick}
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

function SidebarContents({ onClose }: { onClose?: () => void }) {
  const { updateAvailable, currentVersion, latestVersion, releaseUrl, upgradeAvailable } = useUpdateCheck()
  const [upgrading, setUpgrading] = useState(false)
  return (
    <aside className="w-60 bg-muted border-r border-border flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-border shrink-0">
        <JenticLogo />
        {onClose && (
          <button
            onClick={onClose}
            className="ml-auto p-1.5 rounded hover:bg-muted-foreground/20 transition-colors"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-1">
        <NavLink to="/" exact icon={<span>📊</span>} label="Dashboard" onClick={onClose} />
        <NavLink to="/search" icon={<span>🔍</span>} label="Search" onClick={onClose} />

        <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">
          Directory
        </div>
        <NavLink to="/catalog" icon={<span>📚</span>} label="API Catalog" onClick={onClose} />
        <NavLink to="/workflows" icon={<span>🌐</span>} label="Workflows" onClick={onClose} />

        <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">
          Security
        </div>
        <NavLink to="/toolkits" icon={<span>🛡️</span>} label="Toolkits" onClick={onClose} />
        <NavLink to="/credentials" icon={<span>🔐</span>} label="Credentials" onClick={onClose} />
        <NavLink to="/oauth-brokers" icon={<span>🔗</span>} label="OAuth Brokers" onClick={onClose} />

        <div className="mt-4 mb-2 text-[10px] font-mono tracking-widest uppercase text-primary/60 px-4">
          Observability
        </div>
        <NavLink to="/traces" icon={<span>📈</span>} label="Traces" onClick={onClose} />
        <NavLink to="/jobs" icon={<span>⚙️</span>} label="Async Jobs" onClick={onClose} />
      </nav>

      <div className="px-3 py-3 border-t border-border shrink-0">
        {updateAvailable && (
          <div className="px-4 py-2 mb-1 rounded-md text-xs bg-amber-50 dark:bg-amber-950/40">
            <div className="flex items-center gap-2 font-semibold text-amber-600 dark:text-amber-400">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse shrink-0" />
              Update available: {latestVersion}
            </div>
            {upgradeAvailable ? (
              <button
                onClick={async () => {
                  setUpgrading(true)
                  try {
                    await fetch('/admin/upgrade', { method: 'POST' })
                  } catch { /* app will go offline during restart */ }
                }}
                disabled={upgrading}
                className="mt-1.5 w-full px-2 py-1 rounded text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 transition-colors"
              >
                {upgrading ? 'Updating...' : 'Update now'}
              </button>
            ) : releaseUrl ? (
              <a
                href={releaseUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="block mt-1 text-[10px] text-amber-600/70 dark:text-amber-400/70 hover:underline"
              >
                View release notes
              </a>
            ) : null}
          </div>
        )}
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
        {currentVersion && (
          <div className="px-4 pt-2 text-[10px] font-mono text-muted-foreground/50">
            v{currentVersion}
          </div>
        )}
      </div>
    </aside>
  )
}

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user } = useAuth()
  const { data: pendingRequests } = usePendingRequests()
  const queryClient = useQueryClient()

  const logoutMutation = useMutation({
    mutationFn: () => UserService.logoutUserLogoutPost(),
    onSuccess: () => {
      queryClient.clear()
      window.location.href = '/login'
    },
  })

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Desktop sidebar — always visible on md+ */}
      <div className="hidden md:flex md:shrink-0">
        <SidebarContents />
      </div>

      {/* Mobile sidebar — slide-over drawer */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="fixed inset-y-0 left-0 z-50 md:hidden">
            <SidebarContents onClose={() => setSidebarOpen(false)} />
          </div>
        </>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col bg-background/50 min-w-0">
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-border bg-background/80 backdrop-blur shrink-0">
          <div className="flex items-center gap-3">
            {/* Hamburger — mobile only */}
            <button
              className="md:hidden p-2 rounded-md hover:bg-muted transition-colors"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            {/* Logo in header — mobile only (desktop has it in sidebar) */}
            <div className="md:hidden">
              <JenticLogo />
            </div>
          </div>

          <div className="flex items-center gap-4">
            {pendingRequests && pendingRequests.length > 0 && (
              <Link
                to="/toolkits"
                className="bg-danger/10 text-danger border border-danger/30 rounded-full px-3 py-1 text-sm font-semibold flex items-center gap-2 hover:bg-danger/20 transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-danger animate-pulse" />
                {pendingRequests.length} Pending{' '}
                {pendingRequests.length === 1 ? 'Request' : 'Requests'}
              </Link>
            )}
            <div className="hidden sm:block text-sm font-mono text-muted-foreground">
              {user?.username}
            </div>
            <button
              onClick={() => logoutMutation.mutate()}
              className="text-muted-foreground hover:text-primary transition-colors text-sm"
              title="Log out"
            >
              Logout
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
