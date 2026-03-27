import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge, MethodBadge } from '../components/ui/Badge'
import { Database, RefreshCw, Plus, ChevronRight, ChevronDown, ExternalLink, Download, Search, AlertTriangle, Check, Loader2, Zap, Globe } from 'lucide-react'

type Tab = 'registered' | 'catalog'

// ── Registered APIs tab ───────────────────────────────────────────────────────

function OperationsPanel({ apiId }: { apiId: string }) {
  const { data: opsPage, isLoading } = useQuery({
    queryKey: ['ops', apiId],
    queryFn: () => api.listOperations(apiId, 1, 50),
    staleTime: 60000,
  })
  const ops = (opsPage as any)?.data ?? []
  const total = (opsPage as any)?.total ?? 0

  if (isLoading) return (
    <div className="flex items-center gap-2 py-4 px-5 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" /> Loading operations...
    </div>
  )
  if (ops.length === 0) return (
    <div className="py-4 px-5 text-sm text-muted-foreground">No operations indexed for this API.</div>
  )
  return (
    <div className="border-t border-border bg-background/40">
      <div className="px-5 py-2 border-b border-border/50 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{total} operation{total !== 1 ? 's' : ''}</span>
      </div>
      <div className="divide-y divide-border/50 max-h-72 overflow-y-auto">
        {ops.map((op: any) => (
          <div key={op.id ?? op.operation_id} className="px-5 py-2.5 flex items-start gap-3">
            <MethodBadge method={op.method} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground font-medium truncate">{op.summary ?? op.operation_id}</p>
              <code className="text-xs font-mono text-muted-foreground truncate block">{op.path ?? op.id}</code>
            </div>
          </div>
        ))}
        {total > 50 && (
          <div className="px-5 py-2 text-xs text-muted-foreground text-center">
            + {total - 50} more — use Search to find specific operations
          </div>
        )}
      </div>
    </div>
  )
}

function ApiCard({ entry, defaultOpen = false }: { entry: any; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  const isLocal = entry.source === 'local'

  return (
    <div className={`bg-muted border rounded-xl overflow-hidden transition-all ${open ? 'border-primary/40' : 'border-border'}`}>
      <button className="w-full text-left px-5 py-4 hover:bg-background/50 transition-colors" onClick={() => setOpen(o => !o)}>
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border shrink-0 ${
                isLocal
                  ? 'bg-success/10 text-success border-success/20'
                  : 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
              }`}>
                {isLocal ? <Zap className="h-2.5 w-2.5" /> : <Globe className="h-2.5 w-2.5" />}
                {isLocal ? 'local' : 'catalog'}
              </span>
              {entry.has_credentials && (
                <Badge variant="success" className="text-[10px]">credentials ✓</Badge>
              )}
            </div>
            <p className="font-medium text-foreground">{entry.name ?? entry.id}</p>
            {entry.id !== entry.name && (
              <code className="text-xs font-mono text-muted-foreground">{entry.id}</code>
            )}
            {entry.description && (
              <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{entry.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isLocal && (
              <Link to={`/search?q=${encodeURIComponent(entry.id)}`} onClick={e => e.stopPropagation()}
                className="text-xs text-primary hover:text-primary/80 flex items-center gap-1">
                Search ops
              </Link>
            )}
            {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
          </div>
        </div>
      </button>
      {open && isLocal && <OperationsPanel apiId={entry.id} />}
      {open && !isLocal && (
        <div className="border-t border-border bg-background/40 px-5 py-3 text-sm text-muted-foreground">
          This API is in the public catalog but not yet imported. Add a credential with this API ID to import it automatically.
          <div className="mt-2">
            <Link to={`/credentials/new?api_id=${encodeURIComponent(entry.id)}`}
              className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80">
              <Plus className="h-3 w-3" /> Add credential for {entry.id}
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function RegisteredTab({ q }: { q: string }) {
  const [page, setPage] = useState(1)
  const LIMIT = 20

  const { data: apisPage, isLoading } = useQuery({
    queryKey: ['apis', 'local', page, q],
    queryFn: () => api.listApis(page, LIMIT, 'local', q || undefined),
    staleTime: 30000,
  })

  const apis: any[] = (apisPage as any)?.data ?? []
  const total: number = (apisPage as any)?.total ?? 0
  const totalPages: number = (apisPage as any)?.total_pages ?? 1

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading APIs...</div>

  if (apis.length === 0) return (
    <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl">
      <Database className="h-10 w-10 mx-auto mb-3 opacity-30" />
      <p className="font-medium text-foreground">No APIs registered yet</p>
      <p className="text-sm mt-1 mb-4">Import APIs from the public catalog, or add credentials with an API ID to auto-import them.</p>
      <Link to="/credentials/new" className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 text-sm transition-colors">
        <Plus className="h-4 w-4" /> Add Credential
      </Link>
    </div>
  )

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">{total} API{total !== 1 ? 's' : ''} registered</p>
      <div className="space-y-2">
        {apis.map((entry: any) => <ApiCard key={entry.id} entry={entry} />)}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
            className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors">← Prev</button>
          <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
            className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors">Next →</button>
        </div>
      )}
    </div>
  )
}

// ── Public Catalog tab ────────────────────────────────────────────────────────

type CatalogFilter = 'all' | 'registered' | 'unregistered'

function CatalogTab({ q }: { q: string }) {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<CatalogFilter>('all')
  const [importingId, setImportingId] = useState<string | null>(null)
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set())

  const { data: catalogData, isLoading, error } = useQuery({
    queryKey: ['catalog', q, filter],
    queryFn: () => api.listCatalog(
      q || undefined,
      100,
      filter === 'registered',
      filter === 'unregistered',
    ),
    staleTime: 60000,
  })

  const refreshMutation = useMutation({
    mutationFn: () => api.refreshCatalog(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['apis'] })
    },
  })

  const handleImport = async (entry: any) => {
    const apiId = entry.api_id
    setImportingId(apiId)
    try {
      // Step 1: Get spec URL from catalog
      const catalogRes = await fetch(`/catalog/${apiId}`, { credentials: 'include' })
      if (!catalogRes.ok) {
        const body = await catalogRes.json().catch(() => ({}))
        throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`)
      }
      const catalogEntry = await catalogRes.json()
      if (!catalogEntry.spec_url) {
        throw new Error('No spec URL found for this API in the catalog')
      }

      // Step 2: Import via POST /import
      const importRes = await fetch('/import', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sources: [{
            type: 'url',
            url: catalogEntry.spec_url,
            force_api_id: apiId,
          }],
        }),
      })
      if (!importRes.ok) {
        const body = await importRes.json().catch(() => ({}))
        throw new Error(body.detail || `Import failed (${importRes.status})`)
      }
      const importResult = await importRes.json()
      if (importResult.failed > 0) {
        const err = importResult.results?.[0]?.error || 'Unknown error'
        throw new Error(`Import failed: ${err}`)
      }
      setImportedIds(prev => new Set(prev).add(apiId))
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['apis'] })
    } catch (e: any) {
      alert(`Import failed: ${e.message}`)
    } finally {
      setImportingId(null)
    }
  }

  const catalogEntries: any[] = (catalogData as any)?.data ?? []
  const total: number = (catalogData as any)?.total ?? 0
  const catalogTotal: number = (catalogData as any)?.catalog_total ?? 0
  const manifestAge: number | null = (catalogData as any)?.manifest_age_seconds ?? null
  const isEmpty = (catalogData as any)?.status === 'empty'

  const formatAge = (secs: number) => {
    if (secs < 3600) return `${Math.round(secs / 60)}m ago`
    if (secs < 86400) return `${Math.round(secs / 3600)}h ago`
    return `${Math.round(secs / 86400)}d ago`
  }

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading catalog...</div>

  if (error) return (
    <div className="p-6 text-center text-muted-foreground">
      <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-warning" />
      <p>Failed to load catalog.</p>
      <button onClick={() => queryClient.invalidateQueries({ queryKey: ['catalog'] })}
        className="mt-3 text-sm text-primary hover:underline">Try again</button>
    </div>
  )

  if (isEmpty) return (
    <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl space-y-4">
      <Database className="h-10 w-10 mx-auto opacity-30" />
      <div>
        <p className="font-medium text-foreground">Catalog not synced yet</p>
        <p className="text-sm mt-1">Pull the manifest from GitHub to browse available APIs.</p>
      </div>
      <button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}
        className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 text-sm transition-colors disabled:opacity-50">
        <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
        {refreshMutation.isPending ? 'Syncing catalog...' : 'Sync Catalog'}
      </button>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">
            {total} of {catalogTotal} APIs shown
            {manifestAge != null && (
              <span className="ml-2 text-muted-foreground/60">· synced {formatAge(manifestAge)}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Filter */}
          <div className="flex items-center gap-1 bg-muted border border-border rounded-lg p-0.5">
            {(['all', 'registered', 'unregistered'] as CatalogFilter[]).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  filter === f ? 'bg-primary text-background' : 'text-muted-foreground hover:text-foreground'
                }`}>
                {f === 'all' ? 'All' : f === 'registered' ? '✓ Registered' : 'Unregistered'}
              </button>
            ))}
          </div>
          <button onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted border border-border text-muted-foreground hover:text-foreground rounded-lg text-xs transition-colors disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {catalogEntries.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No APIs match your filter.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {catalogEntries.map((entry: any) => {
            const isRegistered = entry.registered || importedIds.has(entry.api_id)
            return (
              <div key={entry.api_id}
                className="flex items-center gap-4 px-5 py-3.5 bg-muted border border-border rounded-xl hover:border-border/80 transition-colors">
                <div className="flex-1 min-w-0 space-y-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-foreground text-sm">{entry.api_id}</p>
                    {isRegistered && <Badge variant="success" className="text-[10px]">registered</Badge>}
                  </div>
                  {entry.description && (
                    <p className="text-xs text-muted-foreground truncate">{entry.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {entry._links?.github && (
                    <a href={entry._links.github} target="_blank" rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                  {isRegistered ? (
                    <Link to={`/search?q=${encodeURIComponent(entry.api_id)}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-xs transition-colors">
                      Search ops
                    </Link>
                  ) : (
                    <button
                      onClick={() => handleImport(entry)}
                      disabled={importingId === entry.api_id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      {importingId === entry.api_id
                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        : <Download className="h-3.5 w-3.5" />
                      }
                      Import
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CatalogPage() {
  const [tab, setTab] = useState<Tab>('registered')
  const [q, setQ] = useState('')

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Discovery</p>
          <h1 className="font-heading text-2xl font-bold text-foreground mt-1">API Catalog</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse your registered APIs and the Jentic public API catalog.
          </p>
        </div>
        <Link to="/credentials/new"
          className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm shrink-0">
          <Plus className="h-4 w-4" /> Add Credential
        </Link>
      </div>

      {/* Tabs + Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1 bg-muted border border-border rounded-lg p-0.5">
          {([
            { key: 'registered', label: 'Your APIs' },
            { key: 'catalog', label: 'Public Catalog' },
          ] as { key: Tab; label: string }[]).map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                tab === t.key ? 'bg-primary text-background' : 'text-muted-foreground hover:text-foreground'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 inset-y-0 my-auto h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Filter by name or API ID..."
            className="w-full bg-muted border border-border rounded-lg pl-8 pr-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-hidden"
          />
        </div>
      </div>

      {tab === 'registered' && <RegisteredTab q={q} />}
      {tab === 'catalog' && <CatalogTab q={q} />}
    </div>
  )
}
