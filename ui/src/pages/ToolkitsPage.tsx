import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { usePendingRequests } from '../hooks/usePendingRequests'
import type { ToolkitCreate } from '../api/types'
import { Plus, Wrench, AlertTriangle, Key, X, Ban } from 'lucide-react'

function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [simulate, setSimulate] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (data: ToolkitCreate) => api.createToolkit(data),
    onSuccess: (t) => { queryClient.invalidateQueries({ queryKey: ['toolkits'] }); onCreated(t.id) },
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-muted border border-border rounded-xl p-6 w-full max-w-md space-y-5 z-10">
        <div className="flex items-center justify-between">
          <h2 className="font-heading font-semibold text-lg text-foreground">Create Toolkit</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
        </div>
        <form onSubmit={e => { e.preventDefault(); setError(null); mutation.mutate({ name, description: description || null, simulate }) }} className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Name *</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} required autoFocus
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden resize-none" />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={simulate} onChange={e => setSimulate(e.target.checked)} className="rounded" />
            <div>
              <span className="text-sm text-foreground">Simulate mode</span>
              <p className="text-xs text-muted-foreground">Returns mock responses without calling real APIs</p>
            </div>
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={mutation.isPending}
              className="flex-1 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 disabled:opacity-50 transition-colors">
              {mutation.isPending ? 'Creating...' : 'Create Toolkit'}
            </button>
            <button type="button" onClick={onClose}
              className="bg-muted border border-border text-foreground rounded-lg px-4 py-2 hover:bg-muted/60 transition-colors">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface ToolkitsPageProps { createNew?: boolean }

export default function ToolkitsPage({ createNew = false }: ToolkitsPageProps) {
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(createNew)

  const { data: toolkits, isLoading } = useQuery({
    queryKey: ['toolkits'],
    queryFn: api.listToolkits,
    refetchInterval: 30000,
  })

  // Pending requests: fetched globally, grouped by toolkit_id here
  const { data: pendingRequests } = usePendingRequests()
  const pendingByToolkit = (pendingRequests ?? []).reduce<Record<string, number>>((acc, req: any) => {
    if (req.toolkit_id) acc[req.toolkit_id] = (acc[req.toolkit_id] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Management</p>
          <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Toolkits</h1>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm">
          <Plus className="h-4 w-4" /> Create Toolkit
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading toolkits...</div>
      ) : !toolkits || toolkits.length === 0 ? (
        <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl">
          <Wrench className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground mb-1">No toolkits yet</p>
          <p className="text-sm mb-4">Create a toolkit to give an agent scoped access to your APIs.</p>
          <button onClick={() => setShowCreate(true)} className="bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm">
            Create your first toolkit
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {toolkits.map(toolkit => {
            const pendingCount = pendingByToolkit[toolkit.id] ?? 0
            return (
              <Link to={`/toolkits/${toolkit.id}`} key={toolkit.id}
                className={`p-5 bg-muted border rounded-xl hover:border-primary/50 hover:bg-muted/80 transition-all block space-y-3 ${toolkit.disabled ? 'border-danger/40 opacity-70' : 'border-border'}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-heading font-semibold text-foreground">{toolkit.name}</h3>
                      {toolkit.disabled && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-danger/10 text-danger border border-danger/30">
                          <Ban className="h-3 w-3" />SUSPENDED
                        </span>
                      )}
                      {pendingCount > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-warning/10 text-warning border border-warning/20">
                          <AlertTriangle className="h-3 w-3" />{pendingCount} pending
                        </span>
                      )}
                      {toolkit.simulate && (
                        <span className="text-[10px] font-mono bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full">simulate</span>
                      )}
                    </div>
                    {toolkit.description && <p className="text-xs text-muted-foreground mt-0.5">{toolkit.description}</p>}
                  </div>
                  <Wrench className="h-4 w-4 text-accent-teal shrink-0 mt-0.5" />
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Key className="h-3 w-3" />{toolkit.key_count ?? '—'} keys</span>
                  <span>{toolkit.credential_count != null ? `${toolkit.credential_count} credentials` : (toolkit.credentials?.length != null ? `${toolkit.credentials.length} credentials` : '—')}</span>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => { setShowCreate(false); if (createNew) navigate('/toolkits') }}
          onCreated={id => { setShowCreate(false); navigate(`/toolkits/${id}`) }}
        />
      )}
    </div>
  )
}
