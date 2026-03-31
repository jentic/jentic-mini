import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { Workflow, ChevronRight, Zap, Globe } from 'lucide-react'

export default function WorkflowsPage() {
  const navigate = useNavigate()

  const { data: workflows, isLoading, isError } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.listWorkflows,
  })

  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Catalog</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Workflows</h1>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading workflows...</div>
      ) : isError ? (
        <div className="p-12 text-center bg-muted border border-border rounded-xl">
          <p className="text-danger font-medium">Failed to load workflows</p>
          <p className="text-sm text-muted-foreground mt-1">Please try refreshing the page.</p>
        </div>
      ) : !workflows || !Array.isArray(workflows) || workflows.length === 0 ? (
        <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl">
          <Workflow className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground">No workflows registered</p>
          <p className="text-sm mt-1">Import an Arazzo workflow file to get started.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {workflows.map((wf: any) => (
            <div
              key={wf.slug}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/workflows/${wf.slug}`)}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(`/workflows/${wf.slug}`) } }}
              className="flex items-center gap-4 px-5 py-3.5 bg-muted border border-border rounded-xl hover:border-primary/40 transition-colors cursor-pointer"
            >
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Workflow className="h-3.5 w-3.5 text-accent-pink shrink-0" />
                  <p className="font-medium text-foreground text-sm truncate">
                    {wf.name ?? wf.slug}
                  </p>
                  <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border shrink-0 ${
                    wf.source === 'local'
                      ? 'bg-success/10 text-success border-success/20'
                      : 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20'
                  }`}>
                    {wf.source === 'local' ? <Zap className="h-2.5 w-2.5" /> : <Globe className="h-2.5 w-2.5" />}
                    {wf.source === 'local' ? 'local' : 'catalog'}
                  </span>
                  {wf.steps_count > 0 && (
                    <Badge variant="default" className="text-[10px]">{wf.steps_count} steps</Badge>
                  )}
                </div>
                {wf.description && (
                  <p className="text-xs text-muted-foreground line-clamp-1">{wf.description}</p>
                )}
                {wf.involved_apis && wf.involved_apis.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    {wf.involved_apis.slice(0, 3).map((apiId: any) => (
                      <Badge key={apiId} variant="default" className="font-mono text-[10px]">{apiId}</Badge>
                    ))}
                    {wf.involved_apis.length > 3 && (
                      <span className="text-[10px] text-muted-foreground">+{wf.involved_apis.length - 3} more</span>
                    )}
                  </div>
                )}
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
