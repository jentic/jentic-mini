import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { usePendingRequests } from '../../hooks/usePendingRequests'
import { JenticLogo } from '../ui/Logo'
import {
  LayoutDashboard,
  Search,
  Database,
  Wrench,
  Key,
  Workflow,
  Activity,
  Briefcase,
  AlertTriangle,
} from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  { path: '/',           label: 'Dashboard',  icon: <LayoutDashboard className="h-4 w-4" /> },
  { path: '/search',     label: 'Search',     icon: <Search className="h-4 w-4" /> },
  { path: '/catalog',    label: 'Catalog',    icon: <Database className="h-4 w-4" /> },
  { path: '/workflows',  label: 'Workflows',  icon: <Workflow className="h-4 w-4" /> },
  { path: '/toolkits',   label: 'Toolkits',   icon: <Wrench className="h-4 w-4" /> },
  { path: '/credentials',label: 'Credentials',icon: <Key className="h-4 w-4" /> },
  { path: '/traces',     label: 'Traces',     icon: <Activity className="h-4 w-4" /> },
  { path: '/jobs',       label: 'Jobs',       icon: <Briefcase className="h-4 w-4" /> },
]

export function Sidebar() {
  const { data: pendingCount } = usePendingRequests()
  const count = Array.isArray(pendingCount) ? pendingCount.length : 0

  return (
    <aside className="w-56 shrink-0 bg-background border-r border-border flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-border">
        <JenticLogo />
      </div>

      {/* Pending requests alert */}
      {count > 0 && (
        <div className="mx-3 mt-3 flex items-center gap-2 bg-warning/10 border border-warning/30 rounded-lg px-3 py-2 text-xs text-warning">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>{count} pending request{count !== 1 ? 's' : ''}</span>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
              }`
            }
          >
            {item.icon}
            <span>{item.label}</span>
            {item.path === '/toolkits' && count > 0 && (
              <span className="ml-auto bg-danger text-white text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center">
                {count > 9 ? '9+' : count}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border">
        <p className="text-[10px] font-mono text-muted-foreground/50">jentic mini · self-hosted</p>
      </div>
    </aside>
  )
}
