import { Component, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { ChevronLeft, Workflow, ExternalLink, Loader2, Zap, AlertTriangle } from 'lucide-react'
import { ArazzoUI } from '@jentic/arazzo-ui'
import '@jentic/arazzo-ui/styles.css'

class ArazzoErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  render() {
    if (this.state.error) {
      return (
        <div className="border border-border rounded-xl p-8 text-center bg-muted">
          <AlertTriangle className="h-8 w-8 text-warning mx-auto mb-3" />
          <p className="text-sm font-medium text-foreground mb-1">Workflow visualization failed to render</p>
          <p className="text-xs text-muted-foreground">{this.state.error.message}</p>
        </div>
      )
    }
    return this.props.children
  }
}

function CatalogWorkflowFallback({ slug, navigate }: { slug: string; navigate: (path: string) => void }) {
  const queryClient = useQueryClient()
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Convert slug back to api_id: apideck.com~ecosystem → apideck.com/ecosystem
  const apiId = slug.replace('~', '/')
  const githubUrl = `https://github.com/jentic/jentic-public-apis/tree/main/workflows/${slug}`
  const encodedSlug = encodeURIComponent(slug)
  const rawArazzoUrl = `https://raw.githubusercontent.com/jentic/jentic-public-apis/refs/heads/main/workflows/${encodedSlug}/workflows.arazzo.json`
  const arazzoUIUrl = `https://arazzo-ui.jentic.com?document=${encodeURIComponent(rawArazzoUrl)}`

  const handleImport = async () => {
    setImporting(true)
    setError(null)
    try {
      const catalogRes = await fetch(`/catalog/${apiId}`, { credentials: 'include' })
      if (!catalogRes.ok) {
        const body = await catalogRes.json().catch(() => ({}))
        throw new Error(body.detail || `Catalog lookup failed (${catalogRes.status})`)
      }
      const catalogEntry = await catalogRes.json()
      if (!catalogEntry.spec_url) {
        throw new Error('No spec URL found for this API in the catalog')
      }
      const importRes = await fetch('/import', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sources: [{ type: 'url', url: catalogEntry.spec_url, force_api_id: apiId }] }),
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
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      navigate('/workflows')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <button onClick={() => navigate('/workflows')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Workflows
      </button>
      <div className="bg-muted border border-border rounded-xl p-6 space-y-4">
        <div className="flex items-start gap-3">
          <Workflow className="h-6 w-6 text-accent-pink mt-0.5 shrink-0" />
          <div>
            <h1 className="font-heading text-xl font-bold text-foreground">{apiId}</h1>
            <p className="text-xs font-mono text-muted-foreground mt-0.5">{slug}</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          This workflow is available in the Jentic public catalog. Import it to view details and execute.
        </p>
        {error && <p className="text-xs text-danger">{error}</p>}
        <div className="flex items-center gap-3">
          <button onClick={handleImport} disabled={importing}
            className="inline-flex items-center gap-1.5 text-sm text-accent-teal hover:text-accent-teal/80 disabled:opacity-50">
            {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {importing ? 'Importing...' : 'Import this workflow'}
          </button>
          <a href={githubUrl} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80">
            <ExternalLink className="h-3.5 w-3.5" /> View on GitHub
          </a>
          <a href={arazzoUIUrl} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80">
            <ExternalLink className="h-3.5 w-3.5" /> View using Arazzo UI
          </a>
        </div>
      </div>
    </div>
  )
}

export default function WorkflowDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [view, setView] = useState<'diagram' | 'docs' | 'split'>('docs')

  const { data: workflow, isLoading, error } = useQuery({
    queryKey: ['workflow', slug],
    queryFn: () => api.getWorkflow(slug!),
    enabled: !!slug,
    retry: (failureCount, err: any) => err?.status !== 404 && failureCount < 2,
  })

  // Fetch the raw Arazzo document
  const { data: arazzoDoc, isLoading: isLoadingArazzo } = useQuery({
    queryKey: ['workflow-arazzo', slug],
    queryFn: async () => {
      const res = await fetch(`/workflows/${slug}`, {
        headers: { 'Accept': 'application/vnd.oai.workflows+json' },
        credentials: 'include',
      })
      if (!res.ok) throw new Error('Failed to fetch Arazzo document')
      return res.json()
    },
    enabled: !!slug && !!workflow,
  })

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading workflow...</div>

  // 404 → show catalog fallback. Other errors → show error state.
  const is404 = (error as any)?.status === 404
  if (error && !is404) {
    return (
      <div className="text-center py-16">
        <AlertTriangle className="h-8 w-8 text-danger mx-auto mb-3" />
        <p className="text-sm text-foreground font-medium">Failed to load workflow</p>
        <p className="text-xs text-muted-foreground mt-1">{(error as any)?.message || 'Unknown error'}</p>
      </div>
    )
  }

  if (!workflow) return <CatalogWorkflowFallback slug={slug!} navigate={navigate} />

  const steps: any[] = workflow.steps ?? []
  const involvedApis: string[] = workflow.involved_apis ?? []

  // Check if description is different from name to avoid duplication
  const showDescription = workflow.description && workflow.description !== workflow.name

  return (
    <div className="space-y-4 max-w-full">
      <button onClick={() => navigate('/workflows')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Workflows
      </button>

      {/* Condensed header */}
      <div className="space-y-3">
        <div className="space-y-1">
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Workflow</p>
          <div className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-accent-pink shrink-0" />
            <h1 className="font-heading text-xl font-bold text-foreground">
              {workflow.name ?? workflow.slug}
            </h1>
          </div>
          <p className="text-xs font-mono text-muted-foreground">{workflow.slug}</p>
        </div>

        {/* Meta badges and view toggle */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {steps.length > 0 && (
              <Badge variant="default">{steps.length} step{steps.length !== 1 ? 's' : ''}</Badge>
            )}
            {involvedApis.map((apiId: string) => (
              <Badge key={apiId} variant="default" className="font-mono text-[10px]">{apiId}</Badge>
            ))}
          </div>

          {/* View toggle */}
          <div className="flex items-center gap-1 bg-muted border border-border rounded-lg p-0.5">
            {(['diagram', 'split', 'docs'] as const).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  view === v ? 'bg-primary text-background' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {v === 'diagram' ? 'Diagram' : v === 'split' ? 'Split' : 'Docs'}
              </button>
            ))}
          </div>
        </div>

        {showDescription && (
          <p className="text-sm text-muted-foreground">{workflow.description}</p>
        )}
      </div>

      {/* Arazzo UI Viewer */}
      {isLoadingArazzo ? (
        <div className="text-center py-16 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
          Loading workflow visualization...
        </div>
      ) : arazzoDoc ? (
        <ArazzoErrorBoundary>
          <div className="border border-border rounded-xl overflow-hidden bg-muted" style={{ height: '800px' }}>
            <ArazzoUI
              document={arazzoDoc}
              view={view}
              onViewChange={setView}
            />
          </div>
        </ArazzoErrorBoundary>
      ) : (
        <div className="text-center py-16 text-muted-foreground">
          Failed to load workflow visualization.
        </div>
      )}
    </div>
  )
}
