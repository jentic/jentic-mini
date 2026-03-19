import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { Badge } from '../components/ui/Badge'
import { ChevronLeft, Workflow, ArrowRight } from 'lucide-react'

export default function WorkflowDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()

  const { data: workflow, isLoading } = useQuery({
    queryKey: ['workflow', slug],
    queryFn: () => api.getWorkflow(slug!),
    enabled: !!slug,
  })

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading workflow...</div>

  if (!workflow) return (
    <div className="text-center py-16 text-muted-foreground">
      <p>Workflow not found.</p>
      <button onClick={() => navigate('/workflows')}
        className="mt-4 px-4 py-2 bg-muted border border-border rounded-lg text-sm">
        Back to Workflows
      </button>
    </div>
  )

  const steps: any[] = workflow.steps ?? []
  const inputs: any[] = workflow.inputs ?? []
  const involvedApis: string[] = workflow.involved_apis ?? []

  return (
    <div className="space-y-6 max-w-4xl">
      <button onClick={() => navigate('/workflows')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Workflows
      </button>

      <div className="space-y-2">
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Workflow</p>
        <div className="flex items-start gap-3">
          <Workflow className="h-6 w-6 text-accent-pink mt-0.5 shrink-0" />
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">
              {workflow.name ?? workflow.slug}
            </h1>
            <p className="text-xs font-mono text-muted-foreground mt-0.5">{workflow.slug}</p>
          </div>
        </div>
        {workflow.description && (
          <p className="text-muted-foreground leading-relaxed">{workflow.description}</p>
        )}
      </div>

      {/* Meta badges */}
      <div className="flex items-center gap-2 flex-wrap">
        {steps.length > 0 && (
          <Badge variant="default">{steps.length} step{steps.length !== 1 ? 's' : ''}</Badge>
        )}
        {involvedApis.map((apiId: string) => (
          <Badge key={apiId} variant="default" className="font-mono text-[10px]">{apiId}</Badge>
        ))}
      </div>

      {/* Inputs */}
      {inputs.length > 0 && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-heading font-semibold text-foreground">Inputs ({inputs.length})</h3>
          </div>
          <div className="divide-y divide-border/50">
            {inputs.map((input: any, i: number) => (
              <div key={i} className="px-5 py-3 flex items-baseline gap-3">
                <code className="font-mono text-accent-teal text-sm shrink-0">{input.name}</code>
                {input.required !== false && (
                  <span className="text-danger text-[10px] font-mono shrink-0">required</span>
                )}
                {input.type && (
                  <span className="text-muted-foreground text-xs font-mono shrink-0">{input.type}</span>
                )}
                {input.description && (
                  <span className="text-muted-foreground text-sm truncate">{input.description}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Steps */}
      {steps.length > 0 && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-heading font-semibold text-foreground">Steps</h3>
          </div>
          <div className="divide-y divide-border/50">
            {steps.map((step: any, i: number) => (
              <div key={step.stepId ?? i} className="px-5 py-4 space-y-2">
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-mono font-bold shrink-0">
                    {i + 1}
                  </span>
                  <span className="font-medium text-foreground">{step.stepId ?? `Step ${i + 1}`}</span>
                  {i < steps.length - 1 && (
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground ml-auto" />
                  )}
                </div>
                {step.description && (
                  <p className="text-sm text-muted-foreground ml-9">{step.description}</p>
                )}
                {step.operationId && (
                  <p className="text-xs font-mono text-accent-teal ml-9">{step.operationId}</p>
                )}
                {step.workflowId && (
                  <p className="text-xs font-mono text-accent-blue ml-9">workflow: {step.workflowId}</p>
                )}
                {/* Step parameters */}
                {step.parameters && Object.keys(step.parameters).length > 0 && (
                  <div className="ml-9 mt-1">
                    <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider mb-1">Parameters</p>
                    <div className="space-y-0.5">
                      {Object.entries(step.parameters).slice(0, 5).map(([k, v]) => (
                        <div key={k} className="flex items-baseline gap-2 text-xs">
                          <code className="text-muted-foreground font-mono">{k}:</code>
                          <span className="text-foreground font-mono truncate">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw (fallback) */}
      {steps.length === 0 && inputs.length === 0 && (
        <div className="bg-muted border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h3 className="font-heading font-semibold text-foreground">Raw Definition</h3>
          </div>
          <div className="px-5 py-4">
            <pre className="text-xs font-mono text-muted-foreground overflow-auto max-h-96">
              {JSON.stringify(workflow, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
