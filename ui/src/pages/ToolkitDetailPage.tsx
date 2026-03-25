import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { KeyCreate } from '../api/types'
import { OneTimeKeyDisplay } from '../components/ui/OneTimeKeyDisplay'
import { ConfirmInline } from '../components/ui/ConfirmInline'
import { Badge } from '../components/ui/Badge'
import { PermissionRuleEditor } from '../components/ui/PermissionRuleEditor'
import { ChevronLeft, Key, Plus, Trash2, Settings, AlertTriangle, Link as LinkIcon, X, Unlink, Edit2, ChevronDown, ChevronUp, Save, Ban, ShieldCheck } from 'lucide-react'

function CredentialPermissionEditor({ toolkitId, credential, onClose }: {
  toolkitId: string
  credential: any
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [rules, setRules] = useState<any[]>([])

  const { data: permissions, isLoading, isError } = useQuery({
    queryKey: ['permissions', toolkitId, credential.credential_id],
    queryFn: () => api.getPermissions(toolkitId, credential.credential_id),
  })

  React.useEffect(() => {
    if (permissions) {
      const agentRules = Array.isArray(permissions) ? permissions.filter((r: any) => !r._comment?.includes('System safety')) : []
      setRules(agentRules)
    }
  }, [permissions])

  const saveMutation = useMutation({
    mutationFn: () => api.setPermissions(toolkitId, credential.credential_id, rules),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolkit', toolkitId] })
      queryClient.invalidateQueries({ queryKey: ['permissions', toolkitId, credential.credential_id] })
      onClose()
    },
  })

  if (isLoading) return (
    <div className="border-t border-border bg-background/50 p-5">
      <p className="text-sm text-muted-foreground">Loading permissions...</p>
    </div>
  )

  if (isError) return (
    <div className="border-t border-border bg-background/50 p-5">
      <p className="text-sm text-danger">Failed to load permissions.</p>
    </div>
  )

  return (
    <div className="border-t border-border bg-background/50 p-5 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-foreground">Permission Rules for {credential.label}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Define which operations this credential can access. System safety rules are always appended.
          </p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground shrink-0">
          <X className="h-4 w-4" />
        </button>
      </div>

      <PermissionRuleEditor rules={rules} onChange={setRules} />

      <div className="flex gap-2 pt-2">
        <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg text-sm disabled:opacity-50 transition-colors">
          <Save className="h-4 w-4" /> {saveMutation.isPending ? 'Saving...' : 'Save Rules'}
        </button>
        <button onClick={onClose}
          className="px-4 py-2 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-sm transition-colors">
          Cancel
        </button>
      </div>

      <div className="pt-3 border-t border-border/50">
        <p className="text-xs text-muted-foreground leading-relaxed">
          <strong>Rules syntax:</strong> Each rule has <code className="font-mono bg-muted px-1 rounded">effect</code> (allow/deny), optional <code className="font-mono bg-muted px-1 rounded">methods</code> (GET, POST, etc.), and optional <code className="font-mono bg-muted px-1 rounded">path</code> regex. Rules are evaluated in order. First match wins.
        </p>
      </div>
    </div>
  )
}

function RequestAccessDialog({ toolkitId, onClose }: { toolkitId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [requestType, setRequestType] = useState<'grant' | 'modify_permissions'>('grant')
  const [credentialId, setCredentialId] = useState('')
  const [reason, setReason] = useState('')
  const [rules, setRules] = useState<any[]>([{ effect: 'allow', path: '', methods: [] }])
  const [error, setError] = useState<string | null>(null)

  const { data: credentials } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => api.listCredentials(),
  })

  const createMutation = useMutation({
    mutationFn: () => api.createAccessRequest(toolkitId, {
      type: requestType,
      credential_id: credentialId,
      rules,
      reason: reason || null,
    }),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['access-requests', toolkitId] })
      alert(`Access request created!\n\nApproval URL: ${data.approve_url || data._links?.approve_ui || 'Check pending requests'}`)
      onClose()
    },
    onError: (e: Error) => setError(e.message),
  })

  const credList = Array.isArray(credentials) ? credentials : []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-muted border border-border rounded-xl p-6 w-full max-w-2xl space-y-5 z-10 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-heading font-semibold text-lg text-foreground">Request Access</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground">
          Create an access request for this toolkit. The admin will be notified and can approve or deny.
        </p>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Request Type</label>
            <select value={requestType} onChange={e => setRequestType(e.target.value as any)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none">
              <option value="grant">Grant — bind a new credential to this toolkit</option>
              <option value="modify_permissions">Modify Permissions — update rules on an existing credential</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">Credential *</label>
            <select value={credentialId} onChange={e => setCredentialId(e.target.value)} required
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none">
              <option value="">Select a credential...</option>
              {credList.map((c: any) => (
                <option key={c.id} value={c.id}>{c.label} {c.api_id ? `(${c.api_id})` : ''}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">Permission Rules</label>
            <PermissionRuleEditor rules={rules} onChange={setRules} />
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">Reason (optional)</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={2}
              placeholder="Explain why you need this access..."
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none resize-none" />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 border border-danger/30 rounded-lg p-3">
              <AlertTriangle className="h-4 w-4 shrink-0" />{error}
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={() => createMutation.mutate()} disabled={!credentialId || createMutation.isPending}
              className="flex-1 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 disabled:opacity-50 transition-colors">
              {createMutation.isPending ? 'Submitting...' : 'Submit Request'}
            </button>
            <button onClick={onClose}
              className="bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg px-4 py-2 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ToolkitDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showKeyCreate, setShowKeyCreate] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [newKey, setNewKey] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showRequestAccess, setShowRequestAccess] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editingPermForCred, setEditingPermForCred] = useState<string | null>(null)

  const { data: toolkit, isLoading } = useQuery({
    queryKey: ['toolkit', id],
    queryFn: () => api.getToolkit(id!),
    enabled: !!id,
    refetchInterval: 30000,
  })

  // FIXED: Keys are NOT returned by get_toolkit; need separate query
  const { data: keysResponse } = useQuery({
    queryKey: ['toolkit-keys', id],
    queryFn: () => api.listKeys(id!),
    enabled: !!id,
    refetchInterval: 30000,
  })

  const { data: pendingReqs } = useQuery({
    queryKey: ['access-requests', id],
    queryFn: () => api.listAccessRequests(id!, 'pending'),
    enabled: !!id,
    refetchInterval: 30000,
  })

  const createKeyMutation = useMutation({
    mutationFn: (d: KeyCreate) => api.createKey(id!, d),
    onSuccess: (data) => {
      setNewKey(data.key)
      setShowKeyCreate(false)
      setKeyName('')
      queryClient.invalidateQueries({ queryKey: ['toolkit-keys', id] })
    },
  })

  const revokeKeyMutation = useMutation({
    mutationFn: (keyId: string) => api.revokeKey(id!, keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['toolkit-keys', id] }),
  })

  const unbindMutation = useMutation({
    mutationFn: (credentialId: string) => api.unbindCredential(id!, credentialId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolkit', id] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: () => api.updateToolkit(id!, { name: editName || null, description: editDesc || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolkit', id] })
      queryClient.invalidateQueries({ queryKey: ['toolkits'] })
      setShowSettings(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteToolkit(id!),
    onSuccess: () => navigate('/toolkits'),
  })

  const killswitchMutation = useMutation({
    mutationFn: (disabled: boolean) => api.updateToolkit(id!, { disabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['toolkit', id] })
      queryClient.invalidateQueries({ queryKey: ['toolkits'] })
    },
  })

  React.useEffect(() => {
    if (toolkit && showSettings) { setEditName(toolkit.name); setEditDesc(toolkit.description ?? '') }
  }, [toolkit, showSettings])

  if (isLoading) return <div className="text-center py-16 text-muted-foreground">Loading toolkit...</div>
  if (!toolkit) return (
    <div className="text-center py-16 text-muted-foreground">
      <p>Toolkit not found.</p>
      <button onClick={() => navigate('/toolkits')} className="mt-4 px-4 py-2 bg-muted border border-border rounded-lg text-sm">Back</button>
    </div>
  )

  const keys = (keysResponse as any)?.keys ?? []
  const pending = (pendingReqs ?? []).filter((r: any) => r.status === 'pending')
  const credentials = toolkit.credentials ?? []

  return (
    <div className="space-y-6 max-w-5xl">
      <button onClick={() => navigate('/toolkits')} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Toolkits
      </button>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Toolkit</p>
          <h1 className="font-heading text-2xl font-bold text-foreground mt-1">{toolkit.name}</h1>
          {toolkit.description && <p className="text-muted-foreground mt-1">{toolkit.description}</p>}
          <div className="flex items-center gap-2 mt-2">
            {toolkit.disabled && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono bg-danger/10 text-danger border border-danger/30">
                <Ban className="h-3 w-3" />SUSPENDED
              </span>
            )}
            {toolkit.simulate && <Badge variant="default">simulate mode</Badge>}
            <span className="text-xs text-muted-foreground font-mono">ID: {toolkit.id}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowRequestAccess(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20 rounded-lg text-sm font-medium transition-colors">
            <Plus className="h-4 w-4" /> Request Access
          </button>
          {id !== 'default' && (
            <button onClick={() => setShowSettings(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-sm transition-colors">
              <Settings className="h-4 w-4" /> Settings
            </button>
          )}
        </div>
      </div>

      {/* Suspended warning banner */}
      {toolkit.disabled && (
        <div className="bg-danger/10 border border-danger/40 rounded-xl p-4 flex items-start gap-3">
          <Ban className="h-5 w-5 text-danger shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-danger text-sm">This toolkit is suspended</p>
            <p className="text-xs text-danger/80 mt-0.5">All API requests from agents using this toolkit are blocked with a 403 error. Restore access below to re-enable.</p>
          </div>
        </div>
      )}

      {/* Pending requests */}
      {pending.length > 0 && (
        <div className="bg-warning/10 border border-warning/30 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <h2 className="font-heading font-semibold text-warning">{pending.length} Pending Access Request{pending.length !== 1 ? 's' : ''}</h2>
          </div>
          {pending.map((req: any) => (
            <div key={req.id} className="flex items-center gap-3 bg-background/40 rounded-lg px-4 py-3">
              <div className="flex-1">
                <Badge variant={req.type === 'grant' ? 'default' : 'pending'}>
                  {req.type === 'grant' ? 'credential access' : 'permission change'}
                </Badge>
                {req.reason && <p className="text-xs text-muted-foreground mt-0.5">{req.reason}</p>}
              </div>
              <button onClick={() => navigate(`/approve/${toolkit.id}/${req.id}`)}
                className="px-3 py-1.5 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg text-sm transition-colors">
                Review
              </button>
            </div>
          ))}
        </div>
      )}

      {/* API Keys */}
      <div className="bg-muted border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-heading font-semibold text-foreground">API Keys ({keys.length})</h3>
          <button onClick={() => setShowKeyCreate(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-background hover:bg-primary/80 rounded-lg text-sm font-medium transition-colors">
            <Plus className="h-4 w-4" /> Create Key
          </button>
        </div>
        <div className="px-5 py-4 space-y-3">
          {newKey && (
            <OneTimeKeyDisplay keyValue={newKey} onConfirm={() => setNewKey(null)} title="New API Key Created" />
          )}
          {showKeyCreate && (
            <div className="p-4 bg-background rounded-lg border border-border space-y-3">
              <p className="text-sm font-semibold text-foreground">Create API Key</p>
              <input type="text" value={keyName} onChange={e => setKeyName(e.target.value)} placeholder="Key name (optional)"
                className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none" />
              <div className="flex gap-2">
                <button onClick={() => createKeyMutation.mutate({ name: keyName || null })} disabled={createKeyMutation.isPending}
                  className="px-3 py-1.5 bg-primary text-background hover:bg-primary/80 rounded-lg text-sm disabled:opacity-50 transition-colors">
                  {createKeyMutation.isPending ? 'Generating...' : 'Generate'}
                </button>
                <button onClick={() => setShowKeyCreate(false)}
                  className="px-3 py-1.5 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-sm transition-colors">Cancel</button>
              </div>
            </div>
          )}
          {keys.length === 0 && !showKeyCreate && !newKey && (
            <p className="text-sm text-muted-foreground">No keys yet. Create one to allow agents to use this toolkit.</p>
          )}
          {keys.map((key: any) => (
            <div key={key.id} className="flex items-center gap-3 p-3 bg-background rounded-lg">
              <Key className="h-4 w-4 text-accent-yellow shrink-0" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground text-sm">{key.label || 'Unnamed Key'}</span>
                  {key.prefix && <code className="text-xs font-mono text-muted-foreground">{key.prefix}...</code>}
                  {key.revoked_at && <Badge variant="danger">revoked</Badge>}
                </div>
                {key.created_at && <p className="text-xs text-muted-foreground">{new Date(key.created_at * 1000).toLocaleString()}</p>}
              </div>
              {!key.revoked_at && (
                <ConfirmInline onConfirm={() => revokeKeyMutation.mutate(key.id)} message="Revoke this key?" confirmLabel="Revoke">
                  <button className="px-2 py-1 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded text-xs transition-colors">
                    Revoke
                  </button>
                </ConfirmInline>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Credentials */}
      <div className="bg-muted border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-heading font-semibold text-foreground">Bound Credentials ({credentials.length})</h3>
          <button onClick={() => navigate('/credentials')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg text-sm transition-colors">
            <LinkIcon className="h-4 w-4" /> Manage Credentials
          </button>
        </div>
        <div className="px-5 py-4 space-y-2">
          {credentials.length === 0 ? (
            <p className="text-sm text-muted-foreground">No credentials bound. Bind credentials to grant this toolkit API access.</p>
          ) : (
            credentials.map((cred: any) => (
              <div key={cred.credential_id} className="bg-background border border-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-foreground text-sm">{cred.label}</span>
                    {cred.api_id && <p className="text-xs text-muted-foreground font-mono truncate">{cred.api_id}</p>}
                    {cred.permissions && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {cred.permissions.filter((r: any) => !r._comment?.includes('System safety')).length} agent rule(s) + system safety
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button onClick={() => setEditingPermForCred(editingPermForCred === cred.credential_id ? null : cred.credential_id)}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-muted border border-border text-muted-foreground hover:text-foreground rounded text-xs transition-colors">
                      <Edit2 className="h-3 w-3" /> Permissions
                      {editingPermForCred === cred.credential_id ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {id !== 'default' && (
                      <ConfirmInline onConfirm={() => unbindMutation.mutate(cred.credential_id)} message="Unbind this credential?" confirmLabel="Unbind">
                        <button className="inline-flex items-center gap-1 px-2 py-1 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded text-xs transition-colors">
                          <Unlink className="h-3 w-3" /> Unbind
                        </button>
                      </ConfirmInline>
                    )}
                  </div>
                </div>
                {editingPermForCred === cred.credential_id && (
                  <CredentialPermissionEditor
                    toolkitId={id!}
                    credential={cred}
                    onClose={() => setEditingPermForCred(null)}
                  />
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Danger Zone */}
      {id !== 'default' && (
        <div className="bg-muted border border-danger/30 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-danger/20">
            <h3 className="font-heading font-semibold text-danger text-sm">Danger Zone</h3>
          </div>
          <div className="px-5 py-4 space-y-3">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-foreground">
                  {toolkit.disabled ? 'Restore access' : 'Kill all access'}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {toolkit.disabled
                    ? 'Re-enable all API requests for agents using this toolkit.'
                    : 'Immediately block all API requests from agents using this toolkit.'}
                </p>
              </div>
              {toolkit.disabled ? (
                <ConfirmInline
                  onConfirm={() => killswitchMutation.mutate(false)}
                  message="Restore access to this toolkit?"
                  confirmLabel="Restore"
                >
                  <button
                    disabled={killswitchMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary/10 border border-primary/40 text-primary hover:bg-primary/20 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    {killswitchMutation.isPending ? 'Restoring...' : 'Restore Access'}
                  </button>
                </ConfirmInline>
              ) : (
                <ConfirmInline
                  onConfirm={() => killswitchMutation.mutate(true)}
                  message="Block all API access for this toolkit immediately?"
                  confirmLabel="Kill Access"
                >
                  <button
                    disabled={killswitchMutation.isPending}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-danger/10 border border-danger/40 text-danger hover:bg-danger/20 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
                  >
                    <Ban className="h-4 w-4" />
                    {killswitchMutation.isPending ? 'Suspending...' : 'Kill All Access'}
                  </button>
                </ConfirmInline>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowSettings(false)} />
          <div className="relative bg-muted border border-border rounded-xl p-6 w-full max-w-md space-y-5 z-10">
            <div className="flex items-center justify-between">
              <h2 className="font-heading font-semibold text-lg text-foreground">Toolkit Settings</h2>
              <button onClick={() => setShowSettings(false)} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Name</label>
                <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Description</label>
                <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={2}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none resize-none" />
              </div>
              <div className="flex gap-2">
                <button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}
                  className="flex-1 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 disabled:opacity-50 transition-colors">
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
                <button onClick={() => setShowSettings(false)}
                  className="bg-muted border border-border text-foreground hover:bg-muted/60 rounded-lg px-4 py-2 transition-colors">Cancel</button>
              </div>
              <div className="pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground mb-3">Danger Zone</p>
                <ConfirmInline onConfirm={() => deleteMutation.mutate()} message="Permanently delete this toolkit?" confirmLabel="Delete Forever">
                  <button className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded-lg text-sm transition-colors">
                    <Trash2 className="h-4 w-4" /> Delete Toolkit
                  </button>
                </ConfirmInline>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Request Access Dialog */}
      {showRequestAccess && (
        <RequestAccessDialog toolkitId={id!} onClose={() => setShowRequestAccess(false)} />
      )}
    </div>
  )
}
