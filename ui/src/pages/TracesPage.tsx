import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { TraceOut } from '../api/generated'
import { Badge, StatusBadge } from '../components/ui/Badge'
import { Activity, ChevronLeft, ChevronRight, Filter } from 'lucide-react'

function timeAgo(ts?: number | null) {
  if (!ts) return '—'
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return `${Math.floor(s/86400)}d ago`
}

export default function TracesPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10))
  const toolkit = searchParams.get('toolkit') || undefined
  const workflow = searchParams.get('workflow') || undefined

  const { data: tracesPage, isLoading } = useQuery({
    queryKey: ['traces', page, toolkit, workflow],
    queryFn: () => api.listTraces({ page, limit: 20, toolkit, workflow }),
  })

  const traces = tracesPage?.traces ?? []
  const total = tracesPage?.total ?? 0
  const totalPages = Math.ceil(total / 20)

  return (
    <div className="space-y-5 max-w-6xl">
      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Observability</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Execution Traces</h1>
      </div>

      {(toolkit || workflow) && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {toolkit && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-primary/10 text-primary border border-primary/20">
              toolkit: {toolkit}
              <button onClick={() => { const p = new URLSearchParams(searchParams); p.delete('toolkit'); setSearchParams(p) }}>✕</button>
            </span>
          )}
          {workflow && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-primary/10 text-primary border border-primary/20">
              workflow: {workflow}
              <button onClick={() => { const p = new URLSearchParams(searchParams); p.delete('workflow'); setSearchParams(p) }}>✕</button>
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading traces...</div>
      ) : traces.length === 0 ? (
        <div className="p-12 text-center bg-muted border border-border rounded-xl text-muted-foreground">
          <Activity className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground">No traces found</p>
          <p className="text-sm mt-1">Traces appear here when agents call the broker.</p>
        </div>
      ) : (
        <>
          <div className="bg-muted border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['Time','Toolkit','Operation / Workflow','Status','Duration'].map(h => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-mono text-muted-foreground uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {traces.map((trace: TraceOut) => (
                    <tr key={trace.id} className="border-b border-border/50 hover:bg-background/50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/traces/${trace.id}`)}>
                      <td className="px-4 py-3 text-muted-foreground font-mono text-xs whitespace-nowrap">{timeAgo(trace.created_at)}</td>
                      <td className="px-4 py-3 text-foreground">{trace.toolkit_id ?? '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground truncate max-w-[300px]">
                        {trace.workflow_id && <span className="mr-2 px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-mono">workflow</span>}
                        {trace.operation_id ?? trace.workflow_id ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        {trace.http_status ? <StatusBadge status={trace.http_status} /> : (
                          <Badge variant={trace.status === 'error' ? 'danger' : 'success'}>{trace.status ?? '—'}</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">{trace.duration_ms != null ? `${trace.duration_ms}ms` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button disabled={page<=1} onClick={() => setPage(p => p-1)} className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors"><ChevronLeft className="h-4 w-4" /></button>
              <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
              <button disabled={page>=totalPages} onClick={() => setPage(p => p+1)} className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors"><ChevronRight className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
