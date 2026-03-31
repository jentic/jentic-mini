import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { Briefcase, ChevronLeft, ChevronRight, X } from 'lucide-react'

function timeAgo(ts?: number | null) {
  if (!ts) return '—'
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return `${Math.floor(s/86400)}d ago`
}

type StatusVariant = 'success' | 'danger' | 'warning' | 'default'
function statusVariant(s?: string | null): StatusVariant {
  if (s === 'complete') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running') return 'warning'
  return 'default'
}

export default function JobsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const statusFilter = searchParams.get('status') || undefined

  const { data: jobsPage, isLoading, isError } = useQuery({
    queryKey: ['jobs', page, statusFilter],
    queryFn: () => api.listJobs({ page, status: statusFilter }),
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.cancelJob(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const jobs: any[] = (jobsPage as any)?.items ?? []
  const total = (jobsPage as any)?.total ?? 0
  const totalPages = Math.ceil(total / 20)

  return (
    <div className="space-y-5 max-w-6xl">
      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Observability</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Background Jobs</h1>
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">Status:</span>
        {([null, 'pending', 'running', 'complete', 'failed'] as (string | null)[]).map(s => (
          <button key={s ?? 'all'} onClick={() => { const p = new URLSearchParams(searchParams); s ? p.set('status',s) : p.delete('status'); setSearchParams(p); setPage(1) }}
            className={`px-3 py-1 rounded-full text-xs font-mono border transition-all ${(statusFilter === s || (s === null && !statusFilter)) ? 'bg-primary/20 text-primary border-primary/40' : 'border-border text-muted-foreground hover:border-primary/40'}`}>
            {s ?? 'all'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading jobs...</div>
      ) : isError ? (
        <div className="p-12 text-center bg-muted border border-border rounded-xl">
          <p className="text-danger font-medium">Failed to load jobs</p>
          <p className="text-sm text-muted-foreground mt-1">Please try refreshing the page.</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 text-center bg-muted border border-border rounded-xl text-muted-foreground">
          <Briefcase className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground">No jobs found</p>
          <p className="text-sm mt-1">{statusFilter ? `No ${statusFilter} jobs.` : 'Background jobs appear here when agents trigger async work.'}</p>
        </div>
      ) : (
        <>
          <div className="bg-muted border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['ID','Kind','Status','Toolkit','Created','Actions'].map(h => (
                      <th key={h} className="text-left px-4 py-3 text-xs font-mono text-muted-foreground uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job: any) => (
                    <tr key={job.id} className="border-b border-border/50 hover:bg-background/50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/jobs/${job.id}`)}>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground truncate max-w-[120px]">{job.id}</td>
                      <td className="px-4 py-3 text-foreground">{job.kind ?? '—'}</td>
                      <td className="px-4 py-3"><Badge variant={statusVariant(job.status)}>{job.status ?? 'unknown'}</Badge></td>
                      <td className="px-4 py-3 text-muted-foreground">{job.toolkit_id ?? '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">{timeAgo(job.created_at)}</td>
                      <td className="px-4 py-3">
                        {(job.status === 'pending' || job.status === 'running') && (
                          <button onClick={e => { e.stopPropagation(); cancelMutation.mutate(job.id) }}
                            className="text-danger hover:text-danger/80 transition-colors" title="Cancel"><X className="h-4 w-4" /></button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button disabled={page<=1} onClick={() => setPage(p=>p-1)} className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors"><ChevronLeft className="h-4 w-4" /></button>
              <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
              <button disabled={page>=totalPages} onClick={() => setPage(p=>p+1)} className="px-3 py-1.5 bg-muted border border-border rounded-lg text-sm disabled:opacity-40 hover:bg-muted/60 transition-colors"><ChevronRight className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
