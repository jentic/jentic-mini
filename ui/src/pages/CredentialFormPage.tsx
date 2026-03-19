import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { CredentialCreate, CredentialPatch } from '../api/types'
import { ChevronLeft, AlertTriangle } from 'lucide-react'

export default function CredentialFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEdit = !!id

  const [label, setLabel] = useState('')
  const [apiId, setApiId] = useState('')
  const [schemeName, setSchemeName] = useState('')
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: existing } = useQuery({
    queryKey: ['credential', id],
    queryFn: () => api.getCredential(id!),
    enabled: isEdit,
  })

  useEffect(() => {
    if (existing) {
      setLabel(existing.label)
      setApiId(existing.api_id ?? '')
      setSchemeName(existing.scheme_name ?? '')
    }
  }, [existing])

  const createMutation = useMutation({
    mutationFn: (d: CredentialCreate) => api.createCredential(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['credentials'] }); navigate('/credentials') },
    onError: (e: Error) => setError(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: (d: CredentialPatch) => api.updateCredential(id!, d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['credentials'] }); navigate('/credentials') },
    onError: (e: Error) => setError(e.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (isEdit) {
      updateMutation.mutate({ label: label || null, api_id: apiId || null, scheme_name: schemeName || null, value: value || null })
    } else {
      if (!value) { setError('Credential value is required'); return }
      createMutation.mutate({ label, api_id: apiId || null, scheme_name: schemeName || null, value })
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <div className="space-y-6 max-w-2xl">
      <button onClick={() => navigate('/credentials')} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Credentials
      </button>

      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Management</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">{isEdit ? 'Edit Credential' : 'Add Credential'}</h1>
      </div>

      <form onSubmit={handleSubmit} className="bg-muted border border-border rounded-xl p-6 space-y-5">
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Label *</label>
          <input type="text" value={label} onChange={e => setLabel(e.target.value)} required autoFocus
            placeholder="e.g. My OpenAI API Key"
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none" />
          <p className="text-xs text-muted-foreground mt-1">Human-readable name for this credential</p>
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1">API ID</label>
          <input type="text" value={apiId} onChange={e => setApiId(e.target.value)}
            placeholder="e.g. openai/v1"
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:border-primary focus:outline-none" />
          <p className="text-xs text-muted-foreground mt-1">Optional: API identifier for auto-binding</p>
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1">Auth Scheme Name</label>
          <input type="text" value={schemeName} onChange={e => setSchemeName(e.target.value)}
            placeholder="e.g. BearerAuth, ApiKeyHeader"
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:border-primary focus:outline-none" />
          <p className="text-xs text-muted-foreground mt-1">Optional: matches OpenAPI securitySchemes</p>
        </div>

        <div>
          <label className="text-xs text-muted-foreground block mb-1">
            Credential Value {!isEdit && '*'}{isEdit && <span className="text-muted-foreground/60"> (leave blank to keep existing)</span>}
          </label>
          <textarea value={value} onChange={e => setValue(e.target.value)} rows={4} required={!isEdit}
            placeholder="Paste your API key, bearer token, or credentials..."
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:border-primary focus:outline-none resize-none" />
          <p className="text-xs text-muted-foreground mt-1">⚠️ Stored securely. This value will never be shown again after saving.</p>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 border border-danger/30 rounded-lg p-3">
            <AlertTriangle className="h-4 w-4 shrink-0" />{error}
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={isLoading}
            className="flex-1 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 disabled:opacity-50 transition-colors">
            {isLoading ? 'Saving...' : isEdit ? 'Update Credential' : 'Save Credential'}
          </button>
          <button type="button" onClick={() => navigate('/credentials')}
            className="bg-muted border border-border text-foreground rounded-lg px-4 py-2 hover:bg-muted/60 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  )
}
