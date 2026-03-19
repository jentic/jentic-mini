import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Card, CardBody } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Workflow, ChevronRight } from 'lucide-react'

export default function WorkflowsPage() {
  const navigate = useNavigate()

  const { data: workflows, isLoading } = useQuery({
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
      ) : !workflows || workflows.length === 0 ? (
        <Card>
          <CardBody>
            <div className="text-center py-12 text-muted-foreground">
              <Workflow className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="font-medium text-foreground">No workflows registered</p>
              <p className="text-sm mt-1">Import an Arazzo workflow file to get started.</p>
            </div>
          </CardBody>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {workflows.map((wf: any) => (
            <Card
              key={wf.slug}
              hoverable
              onClick={() => navigate(`/workflows/${wf.slug}`)}
              className="p-5 space-y-3"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Workflow className="h-4 w-4 text-accent-pink" />
                  <h3 className="font-heading font-semibold text-foreground">{wf.name ?? wf.slug}</h3>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>

              {wf.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">{wf.description}</p>
              )}

              <div className="flex items-center gap-2 flex-wrap">
                {wf.steps && (
                  <Badge variant="default">{wf.steps.length} steps</Badge>
                )}
                {wf.involved_apis?.map((apiId: any) => (
                  <Badge key={apiId} variant="default" className="font-mono text-[10px]">{apiId}</Badge>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
