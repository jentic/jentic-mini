import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { ChevronLeft, Clock, ExternalLink, X } from 'lucide-react'

type StatusVariant = 'success' | 'danger' | 'warning' | 'default'
function statusVariant(s?: string | null): StatusVariant {
  if (s === 'complete') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running') return 'warning'
  return 'default'
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: job, isLoading } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.getJob(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && (data.status === 'running' || data.status === 'pending')) return 3000
      return false
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelJob(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job', id] }),
  })

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading job...</div>
  if (!job) return (
    <div className="text-center py-16 text-muted-foreground">
      <p>Job not found.</p>
      <button onClick={() => navigate('/jobs')} className="mt-4 px-4 py-2 bg-muted border border-border rounded-lg text-sm">Back to Jobs</button>
    </div>
  )

  return (
    <div className="space-y-6 max-w-4xl">
      <button onClick={() => navigate('/jobs')} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Jobs
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Job Detail</p>
          <h1 className="font-heading text-xl font-bold text-foreground mt-1 font-mono break-all">{job.id}</h1>
        </div>
        {(job.status === 'pending' || job.status === 'running') && (
          <button onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded-lg text-sm disabled:opacity-50 transition-colors">
            <X className="h-4 w-4" /> {cancelMutation.isPending ? 'Cancelling...' : 'Cancel Job'}
          </button>
        )}
      </div>

      {/* Summary */}
      <div className="bg-muted border border-border rounded-xl p-5 space-y-4">
        <h2 className="font-heading font-semibold text-foreground border-b border-border pb-3">Summary</h2>
        <div className="grid grid-cols-2 gap-4">
          <div><p className="text-xs text-muted-foreground mb-1">Status</p><Badge variant={statusVariant(job.status)} className="text-sm">{job.status ?? 'unknown'}</Badge></div>
          <div><p className="text-xs text-muted-foreground mb-1">Kind</p><p className="text-foreground font-medium">{job.kind ?? '—'}</p></div>
          {job.toolkit_id && <div><p className="text-xs text-muted-foreground mb-1">Toolkit</p><code className="text-sm text-accent-teal font-mono">{job.toolkit_id}</code></div>}
          <div><p className="text-xs text-muted-foreground mb-1">Created</p>
            <div className="flex items-center gap-1.5"><Clock className="h-4 w-4 text-muted-foreground" /><span className="text-foreground text-sm">{job.created_at ? new Date(job.created_at * 1000).toLocaleString() : '—'}</span></div>
          </div>
          {job.upstream_job_url && (
            <div className="col-span-2"><p className="text-xs text-muted-foreground mb-1">Upstream Job</p>
              <a href={job.upstream_job_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 text-sm flex items-center gap-1">
                {job.upstream_job_url}<ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
        </div>
      </div>

      {job.result && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border"><h2 className="font-heading font-semibold text-foreground">Result</h2></div>
          <div className="px-5 py-4">
            <pre className="bg-background border border-border rounded-lg p-4 text-xs font-mono text-foreground overflow-auto max-h-96">
              {typeof job.result === 'string' ? job.result : JSON.stringify(job.result, null, 2)}
            </pre>
          </div>
        </div>
      )}
      {job.error && (
        <div className="bg-muted border border-danger/30 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-danger/30"><h2 className="font-heading font-semibold text-danger">Error</h2></div>
          <div className="px-5 py-4">
            <pre className="bg-danger/10 border border-danger/30 rounded-lg p-4 text-xs font-mono text-danger overflow-auto">{job.error}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
