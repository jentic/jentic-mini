import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { oauthBrokers } from '../api/client'
import type { OAuthBroker, OAuthAccount, ConnectLinkResponse } from '../api/client'
import { Link2, Plus, Trash2, RefreshCw, ExternalLink, ChevronDown, ChevronRight, Shield } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ConfirmInline } from '../components/ui/ConfirmInline'

// ── Add Broker Form ──────────────────────────────────────────────

function AddBrokerForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    id: '',
    type: 'pipedream',
    client_id: '',
    client_secret: '',
    project_id: '',
    environment: 'production',
    default_external_user_id: 'default',
  })

  const createMutation = useMutation({
    mutationFn: () =>
      oauthBrokers.create({
        id: form.id,
        type: form.type,
        config: {
          client_id: form.client_id,
          client_secret: form.client_secret,
          project_id: form.project_id,
          environment: form.environment,
          default_external_user_id: form.default_external_user_id,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] })
      onClose()
    },
  })

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [field]: e.target.value }))

  const inputClass =
    'w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50'

  return (
    <div className="bg-muted border border-border rounded-xl p-4 space-y-4">
      <h3 className="text-sm font-medium text-foreground">Add OAuth Broker</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Broker ID</label>
          <input className={inputClass} value={form.id} onChange={set('id')} placeholder="e.g. pipedream" />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Type</label>
          <select className={inputClass} value={form.type} onChange={set('type')}>
            <option value="pipedream">pipedream</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Client ID</label>
          <input className={inputClass} value={form.client_id} onChange={set('client_id')} placeholder="OAuth client ID" />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Client Secret</label>
          <input className={inputClass} type="password" value={form.client_secret} onChange={set('client_secret')} placeholder="OAuth client secret" />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Project ID</label>
          <input className={inputClass} value={form.project_id} onChange={set('project_id')} placeholder="Pipedream project ID" />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Environment</label>
          <input className={inputClass} value={form.environment} onChange={set('environment')} />
        </div>
        <div className="col-span-2">
          <label className="block text-xs text-muted-foreground mb-1">Default External User ID</label>
          <input className={inputClass} value={form.default_external_user_id} onChange={set('default_external_user_id')} />
        </div>
      </div>

      {createMutation.isError && (
        <p className="text-xs text-danger">{(createMutation.error as Error).message}</p>
      )}

      <div className="flex items-center gap-2">
        <Button onClick={() => createMutation.mutate()} loading={createMutation.isPending} disabled={!form.id || !form.client_id || !form.client_secret || !form.project_id}>
          Create Broker
        </Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
    </div>
  )
}

// ── Connect Account Panel ────────────────────────────────────────

function CatalogSearch({ onSelect, mirrorValue }: { onSelect: (apiId: string) => void; mirrorValue?: string }) {
  const [q, setQ] = useState('')
  const [dirty, setDirty] = useState(false)
  const [selected, setSelected] = useState('')

  // Mirror the slug value unless user has manually edited the search field
  useEffect(() => {
    if (!dirty && mirrorValue !== undefined) {
      setQ(mirrorValue)
    }
  }, [mirrorValue, dirty])

  const { data, isLoading } = useQuery({
    queryKey: ['catalog-search', q],
    queryFn: () => fetch(`/catalog?q=${encodeURIComponent(q)}&limit=10`, { credentials: 'include' })
      .then(r => r.json()),
    enabled: q.length >= 2,
  })

  const entries: any[] = data?.data ?? []

  if (selected) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono bg-muted px-2 py-1 rounded">{selected}</span>
        <button className="text-xs text-muted-foreground underline" onClick={() => { setSelected(''); onSelect('') }}>change</button>
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      <input
        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
        value={q}
        onChange={e => { setQ(e.target.value); if (e.target.value === '') { setDirty(false) } else { setDirty(true) }; setSelected('') }}
        placeholder="Search catalog, e.g. gmail, slack, github"
      />
      {q.length >= 2 && (
        <div className="border border-border rounded-lg overflow-hidden max-h-40 overflow-y-auto">
          {isLoading ? (
            <p className="text-xs text-muted-foreground p-2">Searching...</p>
          ) : entries.length === 0 ? (
            <p className="text-xs text-muted-foreground p-2">No results for "{q}"</p>
          ) : entries.map((e: any) => (
            <button
              key={e.api_id}
              className="w-full text-left px-3 py-2 text-xs hover:bg-muted border-b border-border last:border-0 font-mono"
              onClick={() => { setSelected(e.api_id); setQ(''); onSelect(e.api_id) }}
            >
              {e.api_id}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ConnectAccountPanel({ brokerId, externalUserId, onDone }: { brokerId: string; externalUserId: string; onDone?: () => void }) {
  const [appSlug, setAppSlug] = useState('')
  const [label, setLabel] = useState('')
  const [apiId, setApiId] = useState('')
  const [connectLink, setConnectLink] = useState<ConnectLinkResponse | null>(null)

  const linkMutation = useMutation({
    mutationFn: () =>
      oauthBrokers.connectLink(brokerId, {
        app: appSlug,
        external_user_id: externalUserId,
        label: label || appSlug,
        api_id: apiId || undefined,
      }),
    onSuccess: (data) => setConnectLink(data),
  })

  const inputClass =
    'w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50'

  if (connectLink) {
    return (
      <div className="bg-background border border-primary/30 rounded-xl p-4 space-y-3">
        <p className="text-sm font-medium text-foreground">Connect your account</p>
        <a
          href={connectLink.connect_link_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm"
        >
          <ExternalLink className="h-4 w-4" />
          Open Connect Link
        </a>
        <p className="text-xs text-muted-foreground">
          Click the link above to connect your account in Pipedream. Return here and click <strong>Done</strong> when finished — this will sync your new connection automatically.
        </p>
        <Button variant="ghost" size="sm" onClick={() => { setConnectLink(null); onDone?.() }}>Done — Sync Now</Button>
      </div>
    )
  }

  return (
    <div className="bg-background border border-border rounded-xl p-4 space-y-3">
      <p className="text-sm font-medium text-foreground">Connect a new account</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-muted-foreground mb-1">App Slug</label>
          <input className={inputClass} value={appSlug} onChange={e => setAppSlug(e.target.value)} placeholder="e.g. gmail, slack, github" />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Label (optional)</label>
          <input className={inputClass} value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. My Gmail" />
        </div>
      </div>
      <div>
        <label className="block text-xs text-muted-foreground mb-1">Catalog API <span className="text-danger">*</span></label>
        <CatalogSearch onSelect={setApiId} mirrorValue={appSlug} />
      </div>
      {linkMutation.isError && (
        <p className="text-xs text-danger">{(linkMutation.error as Error).message}</p>
      )}
      <Button size="sm" onClick={() => linkMutation.mutate()} loading={linkMutation.isPending} disabled={!appSlug || !apiId}>
        <ExternalLink className="h-3.5 w-3.5" /> Get Connect Link
      </Button>
    </div>
  )
}

// ── Broker Accounts Section ──────────────────────────────────────

function BrokerAccounts({ broker }: { broker: OAuthBroker }) {
  const queryClient = useQueryClient()
  const externalUserId = broker.config?.default_external_user_id ?? 'default'
  const [showConnect, setShowConnect] = useState(false)
  const [confirmDeleteHost, setConfirmDeleteHost] = useState<string | null>(null)

  const { data: accounts, isLoading } = useQuery({
    queryKey: ['oauth-broker-accounts', broker.id],
    queryFn: () => oauthBrokers.accounts(broker.id, externalUserId),
  })

  const syncMutation = useMutation({
    mutationFn: () => oauthBrokers.sync(broker.id, externalUserId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-broker-accounts', broker.id] })
    },
  })

  const deleteAccountMutation = useMutation({
    mutationFn: (apiHost: string) => oauthBrokers.deleteAccount(broker.id, apiHost, externalUserId),
    onSuccess: () => {
      setConfirmDeleteHost(null)
      queryClient.invalidateQueries({ queryKey: ['oauth-broker-accounts', broker.id] })
    },
  })

  return (
    <div className="space-y-3 mt-3 pl-8">
      <div className="flex items-center gap-2">
        <h4 className="text-xs font-mono tracking-widest uppercase text-muted-foreground">Connected Accounts</h4>
        <Button variant="secondary" size="sm" onClick={() => syncMutation.mutate()} loading={syncMutation.isPending}>
          <RefreshCw className="h-3.5 w-3.5" /> Sync
        </Button>
        <Button variant="secondary" size="sm" onClick={() => setShowConnect(s => !s)}>
          <Plus className="h-3.5 w-3.5" /> Connect Account
        </Button>
      </div>

      {syncMutation.isSuccess && (
        <p className="text-xs text-success">Synced — {syncMutation.data.accounts_synced} account(s) updated.</p>
      )}

      {showConnect && (
        <ConnectAccountPanel brokerId={broker.id} externalUserId={externalUserId} onDone={() => { setShowConnect(false); syncMutation.mutate() }} />
      )}

      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading accounts...</p>
      ) : !accounts || accounts.length === 0 ? (
        <p className="text-xs text-muted-foreground">No connected accounts yet. Use Sync or Connect Account above.</p>
      ) : (
        <div className="space-y-1.5">
          {accounts.map(acc => (
            <div key={acc.api_host} className="border border-border rounded-lg overflow-hidden">
              <div className="flex items-center gap-3 p-3 bg-background text-sm">
                <Shield className="h-4 w-4 text-accent-teal shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-foreground">{acc.label || acc.app_slug}</span>
                    <Badge variant="default" className="text-[10px]">{acc.app_slug}</Badge>
                    {acc.api_host && <span className="text-xs text-muted-foreground font-mono">{acc.api_host}</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs text-muted-foreground">account: {acc.account_id}</span>
                    {acc.synced_at && (
                      <span className="text-xs text-muted-foreground">synced {new Date(acc.synced_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                <Badge variant={acc.healthy ? 'success' : 'danger'} className="text-[10px]">
                  {acc.healthy ? 'healthy' : 'unhealthy'}
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive shrink-0"
                  onClick={() => setConfirmDeleteHost(acc.api_host)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>

              {confirmDeleteHost === acc.api_host && (
                <div className="px-3 pb-3 pt-1 bg-destructive/5 border-t border-border text-xs space-y-2">
                  <p className="font-medium text-destructive">Remove this connection?</p>
                  <p className="text-muted-foreground">This will:</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-0.5 ml-1">
                    <li>Revoke <strong>{acc.label || acc.app_slug}</strong> in Pipedream (upstream provider)</li>
                    <li>Remove the credential from any toolkits it's provisioned to</li>
                    <li>Delete the credential from this instance</li>
                  </ul>
                  {deleteAccountMutation.isError && (
                    <p className="text-destructive">{String(deleteAccountMutation.error)}</p>
                  )}
                  <div className="flex gap-2 pt-1">
                    <Button
                      variant="danger"
                      size="sm"
                      loading={deleteAccountMutation.isPending}
                      onClick={() => deleteAccountMutation.mutate(acc.api_host)}
                    >
                      Remove & Revoke
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setConfirmDeleteHost(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Broker Card ──────────────────────────────────────────────────

function BrokerCard({ broker }: { broker: OAuthBroker }) {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => oauthBrokers.delete(broker.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['oauth-brokers'] }),
  })

  return (
    <div className="bg-muted border border-border rounded-xl p-4">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setExpanded(e => !e)}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </button>
        <Link2 className="h-5 w-5 text-accent-blue shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-foreground">{broker.id}</span>
            <Badge variant="default" className="text-[10px]">{broker.type}</Badge>
            {broker.config?.project_id && (
              <span className="text-xs text-muted-foreground font-mono">project: {broker.config.project_id}</span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            {broker.config?.default_external_user_id && (
              <span className="text-xs text-muted-foreground">user: {broker.config.default_external_user_id}</span>
            )}
            {broker.created_at && (
              <span className="text-xs text-muted-foreground">
                created {new Date(broker.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <ConfirmInline onConfirm={() => deleteMutation.mutate()} message="Delete this broker?" confirmLabel="Delete">
          <button className="inline-flex items-center gap-1 px-3 py-1.5 bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 rounded-lg text-sm transition-colors">
            <Trash2 className="h-4 w-4" />
          </button>
        </ConfirmInline>
      </div>

      {expanded && <BrokerAccounts broker={broker} />}
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────────

export default function OAuthBrokersPage() {
  const [showAdd, setShowAdd] = useState(false)

  const { data: brokers, isLoading } = useQuery({
    queryKey: ['oauth-brokers'],
    queryFn: () => oauthBrokers.list(),
  })

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Management</p>
          <h1 className="font-heading text-2xl font-bold text-foreground mt-1">OAuth Brokers</h1>
        </div>
        <button
          onClick={() => setShowAdd(s => !s)}
          className="inline-flex items-center gap-2 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm"
        >
          <Plus className="h-4 w-4" /> Add Broker
        </button>
      </div>

      <div className="bg-muted border border-border rounded-xl p-4 text-sm text-muted-foreground">
        Manage OAuth brokers for delegated API authentication. Connect external accounts through
        providers like Pipedream and sync them for agent use.
      </div>

      {showAdd && <AddBrokerForm onClose={() => setShowAdd(false)} />}

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Loading brokers...</div>
      ) : !brokers || brokers.length === 0 ? (
        <div className="p-12 text-center text-muted-foreground bg-muted border border-dashed border-border rounded-xl">
          <Link2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium text-foreground mb-1">No OAuth brokers configured</p>
          <p className="text-sm mb-4">Add a broker to connect external accounts for agent OAuth access.</p>
          <button
            onClick={() => setShowAdd(true)}
            className="bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 transition-colors text-sm"
          >
            Add your first broker
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {brokers.map(broker => (
            <BrokerCard key={broker.id} broker={broker} />
          ))}
        </div>
      )}
    </div>
  )
}
