import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { usePendingRequests } from '../hooks/usePendingRequests'
import { api } from '../api/client'

export default function DashboardPage() {
  const { data: pendingRequests } = usePendingRequests()

  const { data: apisPage } = useQuery({
    queryKey: ['apis-count'],
    queryFn: () => api.listApis(1, 1, 'local'),
  })

  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => api.listWorkflows(),
  })

  const { data: toolkits } = useQuery({
    queryKey: ['toolkits'],
    queryFn: () => api.listToolkits(),
  })

  const { data: tracesPage } = useQuery({
    queryKey: ['traces-recent'],
    queryFn: () => api.listTraces({ limit: 10 }),
  })

  const traces = (tracesPage as any)?.traces ?? []

  function timeAgo(ts: number | null | undefined) {
    if (!ts) return ''
    const secs = Math.floor(Date.now() / 1000 - ts)
    if (secs < 60) return `${secs}s ago`
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
    return `${Math.floor(secs / 86400)}d ago`
  }

  function statusColor(status: number | null | undefined) {
    if (!status) return 'text-muted-foreground'
    if (status < 300) return 'text-success'
    if (status < 400) return 'text-accent-yellow'
    return 'text-danger'
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>

      {/* CRITICAL: Pending requests alert banner */}
      {pendingRequests && pendingRequests.length > 0 && (
        <div className="w-full bg-warning/10 border border-warning/30 rounded-xl p-4 shadow-md">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-warning text-lg">⚠️</span>
            <h2 className="text-lg font-bold text-warning">Pending Access Requests</h2>
          </div>
          <div className="flex flex-col gap-3">
            {pendingRequests.map((req: any) => (
              <div key={req.id} className="flex items-center justify-between p-3 bg-muted rounded-lg border border-border">
                <div className="flex flex-col gap-1">
                  <span className="font-semibold text-foreground">{req.toolkit_id}</span>
                  <span className="text-sm text-muted-foreground">
                    {req.type === 'grant' ? '🔑 Requesting access to credential' : '⚙️ Requesting permission change'}
                    {req.reason && <span className="ml-2 italic">— "{req.reason}"</span>}
                  </span>
                  <span className="text-xs text-muted-foreground">{timeAgo(req.created_at)}</span>
                </div>
                {req.approve_url && (
                  <Link
                    to={req.approve_url.replace(window.location.origin, '')}
                    className="ml-4 shrink-0 bg-warning text-background font-bold rounded-lg px-4 py-2 hover:bg-warning/80 transition-colors text-sm"
                  >
                    Review →
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-muted border border-border rounded-xl p-4">
          <div className="text-xs font-mono uppercase tracking-wider text-primary/60 mb-1">APIs Registered</div>
          <div className="text-3xl font-bold text-foreground">{(apisPage as any)?.total ?? '—'}</div>
        </div>
        <div className="bg-muted border border-border rounded-xl p-4">
          <div className="text-xs font-mono uppercase tracking-wider text-primary/60 mb-1">Active Toolkits</div>
          <div className="text-3xl font-bold text-foreground">{toolkits?.length ?? '—'}</div>
        </div>
        <div className="bg-muted border border-border rounded-xl p-4">
          <div className="text-xs font-mono uppercase tracking-wider text-primary/60 mb-1">Workflows</div>
          <div className="text-3xl font-bold text-foreground">{Array.isArray(workflows) ? workflows.length : '—'}</div>
        </div>
        <div className="bg-muted border border-border rounded-xl p-4">
          <div className="text-xs font-mono uppercase tracking-wider text-primary/60 mb-1">Recent Traces</div>
          <div className="text-3xl font-bold text-foreground">{(tracesPage as any)?.total ?? '—'}</div>
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link to="/search" className="flex items-center justify-center gap-2 bg-muted border border-border rounded-lg px-4 py-3 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
            Search Catalog
          </Link>
          <Link to="/credentials" className="flex items-center justify-center gap-2 bg-muted border border-border rounded-lg px-4 py-3 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
            Add Credential
          </Link>
          <Link to="/toolkits" className="flex items-center justify-center gap-2 bg-muted border border-border rounded-lg px-4 py-3 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
            Create Toolkit
          </Link>
          <Link to="/catalog" className="flex items-center justify-center gap-2 bg-muted border border-border rounded-lg px-4 py-3 text-sm font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
            Import an API
          </Link>
        </div>
      </div>

      {/* Recent executions */}
      <div>
        <h2 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3">Recent Executions</h2>
        {traces.length === 0 ? (
          <div className="bg-muted border border-border rounded-xl p-8 text-center text-muted-foreground">
            No executions yet. Traces appear here when agents call the broker.
          </div>
        ) : (
          <div className="bg-muted border border-border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs font-mono uppercase">
                  <th className="text-left px-4 py-3">Time</th>
                  <th className="text-left px-4 py-3">Toolkit</th>
                  <th className="text-left px-4 py-3">Operation</th>
                  <th className="text-left px-4 py-3">Status</th>
                  <th className="text-left px-4 py-3">Duration</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((t: any) => (
                  <tr key={t.id} className="border-b border-border/50 hover:bg-background/50 transition-colors">
                    <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{timeAgo(t.created_at)}</td>
                    <td className="px-4 py-3 text-foreground">{t.toolkit_id ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground truncate max-w-[200px]">
                      {t.operation_id ?? t.workflow_id ?? '—'}
                    </td>
                    <td className={`px-4 py-3 font-mono font-bold ${statusColor(t.http_status)}`}>
                      {t.http_status ?? t.status}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{t.duration_ms ? `${t.duration_ms}ms` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
