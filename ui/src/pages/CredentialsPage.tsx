import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { Key, Plus, Trash2, Settings } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ConfirmInline } from '../components/ui/ConfirmInline'

export default function CredentialsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: credentials, isLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => api.listCredentials(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCredential(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['credentials'] }),
  })

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Management</p>
          <h1 className="font-heading text-2xl font-bold text-foreground mt-1">Credentials Vault</h1>
        </div>
        <button onClick={() => navigate('/credentials/new')}
          className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm">
          <Plus className="h-4 w-4" /> Add Credential
        </button>
      </div>

      <div className="bg-muted border border-border rounded-xl p-4 text-sm text-muted-foreground">
        Store API credentials securely. Bind them to toolkits to give agents scoped access to external APIs.
        Values are write-only — they are never returned by the API.
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading credentials...</div>
      ) : !credentials || credentials.length === 0 ? (
        <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl">
          <Key className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground mb-1">No credentials stored</p>
          <p className="text-sm mb-4">Add a credential to authenticate agents with external APIs.</p>
          <button onClick={() => navigate('/credentials/new')}
            className="bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm">
            Add your first credential
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {credentials.map(cred => (
            <div key={cred.id} className="flex items-center gap-3 p-4 bg-muted border border-border rounded-xl">
              <Key className="h-5 w-5 text-accent-yellow shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-foreground">{cred.label}</span>
                  {cred.api_id && <span className="text-xs text-muted-foreground font-mono">{cred.api_id}</span>}
                  {cred.scheme_name && <Badge variant="default" className="text-[10px]">{cred.scheme_name}</Badge>}
                </div>
                {cred.created_at && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Added {new Date(cred.created_at * 1000).toLocaleDateString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => navigate(`/credentials/${cred.id}/edit`)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-sm transition-colors">
                  <Settings className="h-4 w-4" /> Edit
                </button>
                <ConfirmInline onConfirm={() => deleteMutation.mutate(cred.id)} message="Delete this credential?" confirmLabel="Delete">
                  <button className="inline-flex items-center gap-1 px-3 py-1.5 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded-lg text-sm transition-colors">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </ConfirmInline>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
