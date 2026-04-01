import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge, MethodBadge } from '../components/ui/Badge'
import { Search, X, ChevronDown, ChevronUp, ExternalLink, Copy, Check, Loader2, Zap, Globe } from 'lucide-react'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button onClick={copy} className="text-muted-foreground hover:text-foreground transition-colors">
      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  )
}

function parseCapabilityId(id: string) {
  // FORMAT: METHOD/host/path  e.g. GET/api.stripe.com/v1/customers
  const parts = id.split('/')
  if (parts.length >= 2 && /^[A-Z]+$/.test(parts[0])) {
    return { method: parts[0], host: parts[1], path: '/' + parts.slice(2).join('/') }
  }
  return null
}

function InspectPanel({ capabilityId, onClose }: { capabilityId: string; onClose: () => void }) {
  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['inspect', capabilityId],
    queryFn: () => api.inspectCapability(capabilityId),
    staleTime: 60000,
  })

  if (isLoading) return (
    <div className="flex items-center justify-center p-8">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  )

  if (error || !detail) return (
    <div className="p-4 text-sm text-danger">Failed to load details for this capability.</div>
  )

  const params: any[] = detail.parameters ?? []
  const auth: any[] = detail.auth_instructions ?? []

  return (
    <div className="border-t border-border bg-background/50 p-5 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          {detail.api_context?.name && (
            <p className="text-xs text-muted-foreground font-mono">{detail.api_context.name}</p>
          )}
          {detail.summary && (
            <p className="font-medium text-foreground text-sm">{detail.summary}</p>
          )}
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>

      {detail.description && (
        <p className="text-sm text-muted-foreground leading-relaxed">{detail.description}</p>
      )}

      {/* Parameters */}
      {params.length > 0 && (
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">Parameters</p>
          <div className="space-y-1.5">
            {params.slice(0, 8).map((p: any, i: number) => (
              <div key={i} className="flex items-baseline gap-2 text-sm">
                <code className="font-mono text-accent-teal text-xs shrink-0">{p.name}</code>
                {p.required && <span className="text-danger text-[10px] font-mono">required</span>}
                {p.in && <span className="text-muted-foreground text-[10px]">in {p.in}</span>}
                {p.description && <span className="text-muted-foreground text-xs truncate">{p.description}</span>}
              </div>
            ))}
            {params.length > 8 && (
              <p className="text-xs text-muted-foreground">+ {params.length - 8} more parameters</p>
            )}
          </div>
        </div>
      )}

      {/* Auth */}
      {auth.length > 0 && (
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">Authentication</p>
          <div className="space-y-1">
            {auth.map((a: any, i: number) => (
              <div key={i} className="text-sm text-muted-foreground">
                <span className="font-mono text-accent-yellow text-xs">{a.header || a.scheme || a.type}</span>
                {a.description && <span className="ml-2">{a.description}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Links */}
      <div className="flex items-center gap-3 pt-2 border-t border-border">
        {detail._links?.upstream && (
          <a href={detail._links.upstream} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80">
            <ExternalLink className="h-3 w-3" /> API
          </a>
        )}
        <Link to={`/traces?capability=${encodeURIComponent(capabilityId)}`}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          View traces
        </Link>
      </div>
    </div>
  )
}

function CatalogPanel({ result, onClose }: { result: any; onClose: () => void }) {
  const links = result._links ?? {}
  const queryClient = useQueryClient()
  const [importing, setImporting] = useState(false)
  const [imported, setImported] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const apiId = result.api_id ?? result.id

  const handleImport = async () => {
    setImporting(true)
    setError(null)
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
      setImported(true)
      queryClient.invalidateQueries({ queryKey: ['search'] })
    } catch (e: any) {
      setError(e.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="border-t border-border bg-background/50 p-5 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          <p className="font-medium text-foreground text-sm">{apiId}</p>
          <p className="text-xs text-muted-foreground">
            {imported
              ? 'Imported successfully. Search again to see individual operations.'
              : 'This API is available in the Jentic public catalog. Import it to browse and execute its operations.'}
          </p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="flex items-center gap-3 pt-2 border-t border-border">
        {!imported && (
          <button
            onClick={handleImport}
            disabled={importing}
            className="inline-flex items-center gap-1 text-xs text-accent-teal hover:text-accent-teal/80 disabled:opacity-50"
          >
            {importing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
            {importing ? 'Importing...' : 'Import this API'}
          </button>
        )}
        {links.github && (
          <a href={links.github} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80">
            <ExternalLink className="h-3 w-3" /> View on GitHub
          </a>
        )}
      </div>
    </div>
  )
}

function ResultCard({ result, expanded, onToggle }: {
  result: any
  expanded: boolean
  onToggle: () => void
}) {
  const parsed = parseCapabilityId(result.id ?? '')
  const isLocal = result.source === 'local'

  return (
    <div className={`bg-muted border rounded-xl overflow-hidden transition-all ${expanded ? 'border-primary/50' : 'border-border'}`}>
      <button
        className="w-full text-left px-5 py-4 hover:bg-background/50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Type */}
              <Badge variant={result.type === 'workflow' ? 'pending' : 'default'} className="shrink-0 text-[10px]">
                {result.type ?? 'operation'}
              </Badge>
              {/* Source */}
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border shrink-0 ${
                isLocal
                  ? 'bg-success/10 text-success border-success/20'
                  : 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
              }`}>
                {isLocal ? <Zap className="h-2.5 w-2.5" /> : <Globe className="h-2.5 w-2.5" />}
                {isLocal ? 'local' : 'catalog'}
              </span>
              {/* HTTP method badge for operations */}
              {parsed && <MethodBadge method={parsed.method} />}
            </div>

            <div className="flex items-center gap-2">
              <p className="font-medium text-foreground text-sm">
                {result.summary ?? result.id}
              </p>
            </div>

            {/* Capability ID */}
            <div className="flex items-center gap-1.5">
              <code className="text-xs font-mono text-muted-foreground truncate max-w-xs">
                {result.id}
              </code>
              <CopyButton text={result.id ?? ''} />
            </div>

            {result.description && (
              <p className="text-xs text-muted-foreground line-clamp-2">{result.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {result.score != null && (
              <span className="text-[10px] text-muted-foreground font-mono">
                {Math.round(result.score * 100)}%
              </span>
            )}
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>
      </button>

      {expanded && (
        isLocal
          ? <InspectPanel capabilityId={result.id} onClose={onToggle} />
          : <CatalogPanel result={result} onClose={onToggle} />
      )}
    </div>
  )
}

const EXAMPLE_QUERIES = [
  'send an email',
  'create a Stripe payment',
  'list GitHub pull requests',
  'post a Slack message',
  'get weather forecast',
  'search for documents',
]

export default function SearchPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [input, setInput] = useState(searchParams.get('q') ?? '')
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const [n, setN] = useState(10)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounce
  const handleInput = useCallback((value: string) => {
    setInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setQuery(value.trim())
      setN(10)
      setExpandedId(null)
      setSearchParams(value.trim() ? { q: value.trim() } : {}, { replace: true })
    }, 400)
  }, [setSearchParams])

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [])

  const { data: results, isFetching } = useQuery({
    queryKey: ['search', query, n],
    queryFn: () => api.search(query, n),
    enabled: query.trim().length > 1,
    staleTime: 30000,
    placeholderData: (prev) => prev,
  })

  const hasResults = Array.isArray(results) && results.length > 0
  const showEmpty = query.trim().length > 1 && !isFetching && !hasResults

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Discovery</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Search</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Find operations and workflows by natural language intent. BM25 search over your local registry and the Jentic public catalog.
        </p>
      </div>

      {/* Search input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          {isFetching
            ? <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
            : <Search className="h-4 w-4 text-muted-foreground" />
          }
        </div>
        <input
          autoFocus
          type="text"
          value={input}
          onChange={e => handleInput(e.target.value)}
          placeholder='e.g. "send an email" or "create a payment"'
          aria-label="Search APIs and capabilities"
          className="w-full bg-muted border border-border rounded-xl pl-11 pr-10 py-3.5 text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-hidden text-base"
        />
        {input && (
          <button
            onClick={() => { setInput(''); setQuery(''); setSearchParams({}, { replace: true }); setExpandedId(null) }}
            className="absolute inset-y-0 right-4 flex items-center text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Example queries (shown when empty) */}
      {!query && (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider">Try searching for</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => { setInput(q); setQuery(q); setSearchParams({ q }, { replace: true }) }}
                className="px-3 py-1.5 bg-muted border border-border rounded-full text-sm text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {hasResults && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {results.length} result{results.length !== 1 ? 's' : ''} for <span className="font-medium text-foreground">"{query}"</span>
              {isFetching && <span className="ml-2 text-primary">Updating...</span>}
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Show</span>
              {[10, 20, 50].map(val => (
                <button key={val} onClick={() => setN(val)}
                  className={`px-2 py-0.5 rounded border text-xs transition-colors ${n === val ? 'border-primary text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}>
                  {val}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {results.map((result: any) => (
              <ResultCard
                key={result.id}
                result={result}
                expanded={expandedId === result.id}
                onToggle={() => setExpandedId(prev => prev === result.id ? null : result.id)}
              />
            ))}
          </div>

          {results.length === n && (
            <div className="text-center pt-2">
              <button onClick={() => setN(prev => prev + 10)}
                className="px-4 py-2 bg-muted border border-border rounded-lg text-sm text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors">
                Load more results
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {showEmpty && (
        <div className="text-center py-16 text-muted-foreground">
          <Search className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground">No results for "{query}"</p>
          <p className="text-sm mt-1">Try different keywords, or import an API from the <button onClick={() => navigate('/catalog')} className="text-primary hover:underline">Catalog</button>.</p>
        </div>
      )}
    </div>
  )
}
