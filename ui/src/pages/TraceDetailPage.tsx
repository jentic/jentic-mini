import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge, StatusBadge } from '../components/ui/Badge'
import { ChevronLeft, Clock, Zap } from 'lucide-react'

export default function TraceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: trace, isLoading } = useQuery({
    queryKey: ['trace', id],
    queryFn: () => api.getTrace(id!),
    enabled: !!id,
  })

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading trace...</div>
  if (!trace) return (
    <div className="text-center py-16 text-muted-foreground">
      <p>Trace not found.</p>
      <button onClick={() => navigate('/traces')} className="mt-4 px-4 py-2 bg-muted border border-border rounded-lg text-sm">Back to Traces</button>
    </div>
  )

  return (
    <div className="space-y-6 max-w-4xl">
      <button onClick={() => navigate('/traces')} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Traces
      </button>

      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Trace Detail</p>
        <h1 className="font-heading text-xl font-bold text-foreground mt-1 font-mono break-all">{trace.id}</h1>
      </div>

      {/* Summary */}
      <div className="bg-muted border border-border rounded-xl p-5 space-y-4">
        <h3 className="font-heading font-semibold text-foreground border-b border-border pb-3">Summary</h3>
        <div className="grid grid-cols-2 gap-4">
          <div><p className="text-xs text-muted-foreground mb-1">Toolkit</p><p className="text-foreground font-medium">{trace.toolkit_id ?? '—'}</p></div>
          <div><p className="text-xs text-muted-foreground mb-1">Status</p>
            {trace.http_status ? <StatusBadge status={trace.http_status} /> : <Badge variant={trace.status === 'error' ? 'danger' : 'success'}>{trace.status ?? '—'}</Badge>}
          </div>
          {trace.operation_id && (
            <div className="col-span-2"><p className="text-xs text-muted-foreground mb-1">Operation</p><code className="text-sm text-accent-teal font-mono break-all">{trace.operation_id}</code></div>
          )}
          {trace.workflow_id && (
            <div className="col-span-2"><p className="text-xs text-muted-foreground mb-1">Workflow</p><code className="text-sm text-accent-pink font-mono break-all">{trace.workflow_id}</code></div>
          )}
          {trace.spec_path && (
            <div className="col-span-2"><p className="text-xs text-muted-foreground mb-1">Spec Path</p><code className="text-xs text-muted-foreground font-mono">{trace.spec_path}</code></div>
          )}
          <div><p className="text-xs text-muted-foreground mb-1">Duration</p>
            <div className="flex items-center gap-1.5"><Zap className="h-4 w-4 text-accent-yellow" /><span className="text-foreground font-mono">{trace.duration_ms != null ? `${trace.duration_ms}ms` : '—'}</span></div>
          </div>
          <div><p className="text-xs text-muted-foreground mb-1">Execution Time</p>
            <div className="flex items-center gap-1.5"><Clock className="h-4 w-4 text-muted-foreground" /><span className="text-foreground text-sm">{trace.created_at ? new Date(trace.created_at * 1000).toLocaleString() : '—'}</span></div>
          </div>
          {trace.completed_at && trace.completed_at !== trace.created_at && (
            <div className="col-span-2"><p className="text-xs text-muted-foreground mb-1">Completed</p><span className="text-foreground text-sm">{new Date(trace.completed_at * 1000).toLocaleString()}</span></div>
          )}
        </div>
        {trace.error && (
          <div className="mt-4 p-3 bg-danger/10 border border-danger/30 rounded-lg">
            <p className="text-xs text-muted-foreground mb-1">Error</p>
            <pre className="text-sm text-danger font-mono whitespace-pre-wrap break-words">{trace.error}</pre>
          </div>
        )}
      </div>

      {/* Steps */}
      {trace.steps && trace.steps.length > 0 && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border"><h3 className="font-heading font-semibold text-foreground">Steps ({trace.steps.length})</h3></div>
          <div className="px-5 py-4 space-y-2">
            {trace.steps.map((step: any, i: number) => (
              <div key={i} className="flex gap-3 p-3 bg-background rounded-lg border border-border">
                <div className="h-6 w-6 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-xs font-mono text-primary shrink-0">{i+1}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {step.step_id && <code className="text-xs font-mono text-muted-foreground mr-2">{step.step_id}</code>}
                    {step.operation && <code className="text-sm font-mono text-foreground">{step.operation}</code>}
                    {step.http_status && <StatusBadge status={step.http_status} />}
                    {step.status && !step.http_status && <Badge variant={step.status === 'error' ? 'danger' : 'success'}>{step.status}</Badge>}
                  </div>
                  {step.error && <pre className="text-xs text-danger mt-1 whitespace-pre-wrap break-words font-mono">{String(step.error)}</pre>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Request / Response */}
      {trace.request && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border"><h3 className="font-heading font-semibold text-foreground">Request</h3></div>
          <div className="px-5 py-4">
            <pre className="bg-background border border-border rounded-lg p-4 text-xs font-mono text-foreground overflow-auto max-h-64">{JSON.stringify(trace.request, null, 2)}</pre>
          </div>
        </div>
      )}
      {trace.response && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border"><h3 className="font-heading font-semibold text-foreground">Response</h3></div>
          <div className="px-5 py-4">
            <pre className="bg-background border border-border rounded-lg p-4 text-xs font-mono text-foreground overflow-auto max-h-64">{JSON.stringify(trace.response, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
