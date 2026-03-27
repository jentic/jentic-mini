import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, LogOut, User, ChevronDown } from 'lucide-react'
import { JenticLogo } from '../ui/Logo'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'

interface TopBarProps {
  username?: string
  pendingCount?: number
}

export function TopBar({ username, pendingCount = 0 }: TopBarProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.clear()
      navigate('/login')
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/search?q=${encodeURIComponent(search.trim())}`)
      setSearch('')
    }
  }

  return (
    <header className="sticky top-0 z-40 h-14 bg-background border-b border-border flex items-center px-4 gap-4">
      {/* Logo */}
      <a href="/" className="shrink-0">
        <JenticLogo />
      </a>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search catalog..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-muted border border-border rounded-lg pl-9 pr-4 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-hidden transition-all"
          />
        </div>
      </form>

      <div className="flex-1" />

      {/* Pending requests badge */}
      {pendingCount > 0 && (
        <button
          onClick={() => navigate('/toolkits')}
          className="relative flex items-center gap-1.5 text-sm text-warning hover:text-warning/80 transition-colors"
          title={`${pendingCount} pending access request${pendingCount !== 1 ? 's' : ''}`}
        >
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 h-4 w-4 flex items-center justify-center rounded-full bg-danger text-background text-[10px] font-bold">
            {pendingCount > 9 ? '9+' : pendingCount}
          </span>
        </button>
      )}

      {/* User menu */}
      <div className="relative">
        <button
          onClick={() => setUserMenuOpen(!userMenuOpen)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <User className="h-4 w-4" />
          <span>{username || 'Admin'}</span>
          <ChevronDown className="h-3 w-3" />
        </button>

        {userMenuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
            <div className="absolute right-0 top-full mt-1 w-40 bg-muted border border-border rounded-lg py-1 shadow-xl z-20">
              <button
                onClick={() => {
                  setUserMenuOpen(false)
                  logoutMutation.mutate()
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-background/50 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  )
}
