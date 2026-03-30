import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { CredentialCreate, CredentialPatch, ApiOut } from '../api/types'
import { ChevronLeft, AlertTriangle, Search, Check, ChevronRight, Loader2 } from 'lucide-react'

// ── Helpers ────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

type SchemeType = 'bearer' | 'basic' | 'apiKey' | 'oauth2' | 'unknown'

type RawSchemes = Record<string, { type?: string; scheme?: string }> | null | undefined

interface SchemeOption {
  name: string        // key from securitySchemes (e.g. "bearerAuth")
  type: SchemeType
  label: string       // human label (e.g. "Bearer Token")
}

const SCHEME_TYPE_PRIORITY: SchemeType[] = ['bearer', 'apiKey', 'basic', 'oauth2', 'unknown']
const SCHEME_TYPE_LABELS: Record<SchemeType, string> = {
  bearer: 'Bearer Token',
  apiKey: 'API Key',
  basic: 'Basic Auth',
  oauth2: 'OAuth 2.0',
  unknown: 'Credential',
}

function schemeTypeFromRaw(s: { type?: string; scheme?: string }): SchemeType {
  if (s.type === 'oauth2') return 'oauth2'
  if (s.type === 'http' && s.scheme?.toLowerCase() === 'bearer') return 'bearer'
  if (s.type === 'http' && s.scheme?.toLowerCase() === 'basic') return 'basic'
  if (s.type === 'apiKey') return 'apiKey'
  return 'unknown'
}

/** Returns all scheme options from a spec, sorted by priority. */
function parseSchemeOptions(schemes: RawSchemes): SchemeOption[] {
  if (!schemes || Object.keys(schemes).length === 0) return []
  const options: SchemeOption[] = Object.entries(schemes).map(([name, s]) => {
    const type = schemeTypeFromRaw(s)
    return { name, type, label: SCHEME_TYPE_LABELS[type] }
  })
  // Sort by priority, dedup labels (keep first of each type)
  const seen = new Set<SchemeType>()
  return options
    .sort((a, b) => SCHEME_TYPE_PRIORITY.indexOf(a.type) - SCHEME_TYPE_PRIORITY.indexOf(b.type))
    .filter(o => { if (seen.has(o.type)) return false; seen.add(o.type); return true })
}

function inferSchemeTypeFromSchemes(schemes: RawSchemes): SchemeType {
  const options = parseSchemeOptions(schemes)
  return options[0]?.type ?? 'unknown'
}

function firstSchemeNameFromSchemes(schemes: RawSchemes): string | null {
  if (!schemes) return null
  return Object.keys(schemes)[0] ?? null
}

/** Fetch security schemes for a selected API.
 *  - local API: use already-fetched detail (has security_schemes)
 *  - catalog API: fetch catalog entry → get spec_url → fetch spec → parse securitySchemes
 *  Returns { schemes, loading }
 */
function useApiSchemes(selectedApi: ApiOut | null): { schemes: RawSchemes; loading: boolean } {
  const isCatalog = selectedApi?.source === 'catalog'
  const isLocal = selectedApi?.source === 'local' || (!!selectedApi && !selectedApi.source)

  // Local: fetch full API detail
  const { data: localDetail, isLoading: localLoading } = useQuery({
    queryKey: ['api-detail', selectedApi?.id],
    queryFn: () => api.getApi(selectedApi!.id),
    enabled: !!selectedApi && isLocal,
  })

  // Catalog step 1: get catalog entry to find spec_url
  const { data: catalogEntry, isLoading: entryLoading } = useQuery({
    queryKey: ['catalog-entry', selectedApi?.id],
    queryFn: () => api.getCatalogEntry(selectedApi!.id),
    enabled: !!selectedApi && isCatalog,
  })

  const specUrl: string | null = (catalogEntry as any)?.spec_url ?? null

  // Catalog step 2: fetch the raw spec from GitHub (public, no auth)
  const { data: spec, isLoading: specLoading } = useQuery({
    queryKey: ['spec', specUrl],
    queryFn: async () => {
      const res = await fetch(specUrl!)
      if (!res.ok) throw new Error(`Failed to fetch spec: ${res.status}`)
      return res.json()
    },
    enabled: !!specUrl,
    staleTime: 5 * 60 * 1000, // cache for 5 min
  })

  if (isLocal) {
    const schemes = (localDetail as any)?.security_schemes as RawSchemes
    return { schemes, loading: localLoading }
  }

  if (isCatalog) {
    const schemes = (spec as any)?.components?.securitySchemes as RawSchemes
    return { schemes, loading: entryLoading || specLoading }
  }

  return { schemes: null, loading: false }
}

// ── Step 1 — API Picker ────────────────────────────────────────────────────

function ApiPicker({ onSelect }: { onSelect: (api: ApiOut) => void }) {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounce(query, 250)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const { data, isLoading } = useQuery({
    queryKey: ['apis-search', debouncedQuery],
    queryFn: () => api.listApis(1, 30, undefined, debouncedQuery),
    enabled: debouncedQuery.length > 0,
    placeholderData: prev => prev,
  })

  const items = (data?.items ?? (data as any)?.data ?? []) as ApiOut[]
  const local = items.filter((a: ApiOut) => a.source === 'local')
  const catalog = items.filter((a: ApiOut) => a.source === 'catalog')

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search APIs (GitHub, Gmail, Stripe…)"
          className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2.5 text-foreground focus:border-primary focus:outline-hidden"
        />
        {isLoading && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />}
      </div>

      {items.length === 0 && !isLoading && debouncedQuery && (
        <p className="text-sm text-muted-foreground text-center py-4">No APIs found for "{debouncedQuery}"</p>
      )}

      {local.length > 0 && (
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-muted-foreground mb-1.5 px-1">Available locally</p>
          <div className="space-y-1">
            {local.map((a: ApiOut) => <ApiRow key={a.id} api={a} onSelect={onSelect} />)}
          </div>
        </div>
      )}

      {catalog.length > 0 && (
        <div>
          <p className="text-[10px] font-mono tracking-widest uppercase text-muted-foreground mb-1.5 px-1">From public catalog</p>
          <div className="space-y-1">
            {catalog.map((a: ApiOut) => <ApiRow key={a.id} api={a} onSelect={onSelect} />)}
          </div>
        </div>
      )}

      {!debouncedQuery && items.length === 0 && !isLoading && (
        <p className="text-sm text-muted-foreground text-center py-6">Start typing to search 10,000+ APIs</p>
      )}
    </div>
  )
}

function ApiRow({ api: a, onSelect }: { api: ApiOut; onSelect: (api: ApiOut) => void }) {
  const hasCreds = !!a.has_credentials
  return (
    <button
      type="button"
      onClick={() => onSelect(a)}
      className="w-full flex items-center justify-between gap-3 bg-background hover:bg-muted/60 border border-border rounded-lg px-3 py-2.5 text-left transition-colors group"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-foreground truncate">{a.name ?? a.id}</span>
          {hasCreds && <span className="text-[10px] bg-success/15 text-success border border-success/30 rounded px-1.5 py-0.5 font-mono shrink-0">configured</span>}
        </div>
        {a.description && <p className="text-xs text-muted-foreground truncate mt-0.5">{a.description as string}</p>}
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:text-foreground transition-colors" />
    </button>
  )
}

// ── Step 2 — Credential Fields ─────────────────────────────────────────────

interface CredFieldsProps {
  selectedApi: ApiOut
  onBack: () => void
  onSaved: () => void
  editId?: string
  existing?: any
}

function CredentialFields({ selectedApi, onBack, onSaved, editId, existing }: CredFieldsProps) {
  const queryClient = useQueryClient()
  const isEdit = !!editId

  // Fetch security schemes from spec (local: API detail, catalog: raw spec via GitHub)
  const { schemes, loading: schemesLoading } = useApiSchemes(selectedApi)
  const schemeOptions = parseSchemeOptions(schemes)
  const defaultScheme = schemeOptions[0] ?? null
  const [selectedScheme, setSelectedScheme] = useState<SchemeOption | null>(null)

  // Reset scheme selection and fields when API changes
  useEffect(() => {
    setSelectedScheme(null)
    setLabel(selectedApi.name ?? selectedApi.id)
    setValue('')
    setIdentity('')
    setError(null)
  }, [selectedApi.id])

  // Prefill from existing credential in edit mode
  useEffect(() => {
    if (existing) {
      setLabel(existing.label ?? '')
      setIdentity(existing.identity ?? '')
      // value is write-only — leave blank
    }
  }, [existing])

  const activeScheme = selectedScheme ?? defaultScheme
  const schemeType = activeScheme?.type ?? 'unknown'
  const schemeName = activeScheme?.name ?? firstSchemeNameFromSchemes(schemes)

  const [label, setLabel] = useState(existing?.label ?? selectedApi.name ?? selectedApi.id)
  const [value, setValue] = useState('')
  const [identity, setIdentity] = useState(existing?.identity ?? '')
  const [error, setError] = useState<string | null>(null)

  // For OAuth, show a different CTA
  const hasOAuthBroker = !!(selectedApi.oauth_broker_id as string | undefined)

  const createMutation = useMutation({
    mutationFn: (d: CredentialCreate) => api.createCredential(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['credentials'] }); onSaved() },
    onError: (e: Error) => setError(e.message),
  })

  const updateMutation = useMutation({
    mutationFn: (d: CredentialPatch) => api.updateCredential(editId!, d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['credentials'] }); onSaved() },
    onError: (e: Error) => setError(e.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (schemeType === 'oauth2') return
    setError(null)

    // Derive auth_type from scheme
    const authTypeMap: Record<SchemeType, CredentialCreate['auth_type']> = {
      bearer: 'bearer',
      apiKey: 'apiKey',
      basic: 'basic',
      oauth2: undefined,
      unknown: undefined,
    }

    if (isEdit) {
      updateMutation.mutate({
        label: label || null,
        api_id: selectedApi.id,
        auth_type: authTypeMap[schemeType],
        value: value || null,
        identity: identity || null,
      })
    } else {
      if (!value) { setError('Credential value is required'); return }
      createMutation.mutate({
        label,
        api_id: selectedApi.id,
        auth_type: authTypeMap[schemeType],
        value,
        identity: identity || undefined,
      })
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  if (schemesLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Reading API spec…</span>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Selected API summary */}
      <div className="flex items-center gap-2 bg-muted/50 border border-border rounded-lg px-3 py-2.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">{selectedApi.name ?? selectedApi.id}</p>
          <p className="text-xs text-muted-foreground font-mono truncate">{selectedApi.id}</p>
        </div>
        <button type="button" onClick={onBack} className="text-xs text-muted-foreground hover:text-foreground shrink-0 transition-colors">
          Change
        </button>
      </div>

      {/* Scheme picker — only shown when multiple auth types available */}
      {schemeOptions.length > 1 && (
        <div>
          <label className="text-xs text-muted-foreground block mb-1.5">Auth method</label>
          <div className="flex gap-1.5 flex-wrap">
            {schemeOptions.map(opt => (
              <button
                key={opt.name}
                type="button"
                onClick={() => setSelectedScheme(opt)}
                className={`text-xs rounded-lg px-3 py-1.5 border transition-colors ${
                  activeScheme?.name === opt.name
                    ? 'bg-primary text-background border-primary font-medium'
                    : 'bg-background text-muted-foreground border-border hover:text-foreground'
                }`}
              >{opt.label}</button>
            ))}
          </div>
        </div>
      )}

      {/* Label */}
      <div>
        <label className="text-xs text-muted-foreground block mb-1">Label</label>
        <input type="text" value={label} onChange={e => setLabel(e.target.value)} required
          className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden" />
      </div>

      {/* OAuth flow */}
      {schemeType === 'oauth2' && (() => {
        const apiName = selectedApi.name ?? selectedApi.id
        const prompt = `Please set up OAuth access for ${apiName} (api_id: "${selectedApi.id}") on my Jentic Mini instance at ${window.location.host}, so I can use it in my workflows.`
        return (
          <div className="bg-muted/50 border border-border rounded-lg p-4 space-y-3">
            <p className="text-sm font-medium text-foreground">OAuth required</p>
            <p className="text-xs text-muted-foreground">
              {apiName} uses OAuth 2.0. Ask your agent to set this up — copy the prompt below and send it:
            </p>
            <div className="relative">
              <pre className="text-xs bg-background border border-border rounded p-3 whitespace-pre-wrap break-words text-foreground font-mono leading-relaxed">{prompt}</pre>
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(prompt)}
                className="absolute top-2 right-2 text-[10px] bg-muted border border-border rounded px-2 py-0.5 text-muted-foreground hover:text-foreground transition-colors"
              >Copy</button>
            </div>
            {hasOAuthBroker && (
              <a href="/oauth-brokers" className="inline-block text-xs text-primary hover:underline">
                OAuth broker already configured — connect here →
              </a>
            )}
          </div>
        )
      })()}

      {/* Basic auth: username + password */}
      {schemeType === 'basic' && (
        <>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Username</label>
            <input type="text" value={identity} onChange={e => setIdentity(e.target.value)}
              placeholder="Your username"
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Password {!isEdit && '*'}</label>
            <input type="password" value={value} onChange={e => setValue(e.target.value)} required={!isEdit}
              placeholder={isEdit ? 'Leave blank to keep existing' : 'Your password'}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden" />
          </div>
        </>
      )}

      {/* Bearer / apiKey / unknown: single token field */}
      {(schemeType === 'bearer' || schemeType === 'apiKey' || schemeType === 'unknown') && (
        <div>
          <label className="text-xs text-muted-foreground block mb-1">
            {schemeType === 'bearer' ? 'Bearer Token' : schemeType === 'apiKey' ? 'API Key' : 'Credential Value'}
            {!isEdit && ' *'}
            {isEdit && <span className="text-muted-foreground/60"> (leave blank to keep existing)</span>}
          </label>
          <textarea value={value} onChange={e => setValue(e.target.value)} rows={3} required={!isEdit}
            placeholder="Paste your token or API key…"
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:border-primary focus:outline-hidden resize-none" />
          <p className="text-xs text-muted-foreground mt-1"><AlertTriangle className="inline h-3 w-3 -mt-0.5" /> Stored encrypted. Never shown again after saving.</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-sm text-danger bg-danger/10 border border-danger/30 rounded-lg p-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />{error}
        </div>
      )}

      {schemeType !== 'oauth2' && (
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={isLoading}
            className="flex-1 bg-primary text-background hover:bg-primary/80 font-medium rounded-lg px-4 py-2 disabled:opacity-50 transition-colors">
            {isLoading ? 'Saving…' : isEdit ? 'Update Credential' : 'Save Credential'}
          </button>
          <button type="button" onClick={onBack}
            className="bg-muted border border-border text-foreground rounded-lg px-4 py-2 hover:bg-muted/60 transition-colors">Cancel</button>
        </div>
      )}
    </form>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function CredentialFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id

  const [selectedApi, setSelectedApi] = useState<ApiOut | null>(null)
  const [step, setStep] = useState<'pick' | 'fill'>(isEdit ? 'fill' : 'pick')

  // For edit mode, load the existing credential to pre-select its API
  const { data: existing } = useQuery({
    queryKey: ['credential', id],
    queryFn: () => api.getCredential(id!),
    enabled: isEdit,
  })

  // When editing, fetch the API for the existing credential
  const { data: existingApi } = useQuery({
    queryKey: ['api', existing?.api_id],
    queryFn: () => api.getApi(existing!.api_id!),
    enabled: isEdit && !!existing?.api_id,
  })

  useEffect(() => {
    if (existingApi) {
      setSelectedApi(existingApi as ApiOut)
      setStep('fill')
    } else if (isEdit && existing && !existing.api_id) {
      // No api_id — fall back to picker
      setStep('pick')
    }
  }, [existingApi, existing, isEdit])

  const handleApiSelect = (a: ApiOut) => {
    setSelectedApi(a)
    setStep('fill')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <button onClick={() => navigate('/credentials')} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ChevronLeft className="h-4 w-4" /> Back to Credentials
      </button>

      <div>
        <p className="text-[10px] font-mono tracking-widest uppercase text-primary/60">Management</p>
        <h1 className="font-heading text-2xl font-bold text-foreground mt-1">{isEdit ? 'Edit Credential' : 'Add Credential'}</h1>
      </div>

      {/* Step indicator */}
      {!isEdit && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className={`flex items-center gap-1 ${step === 'pick' ? 'text-foreground font-medium' : 'text-success'}`}>
            {step === 'fill' ? <Check className="h-3 w-3" /> : <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">1</span>}
            Choose API
          </span>
          <ChevronRight className="h-3 w-3" />
          <span className={`flex items-center gap-1 ${step === 'fill' ? 'text-foreground font-medium' : ''}`}>
            <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">2</span>
            Enter credentials
          </span>
        </div>
      )}

      <div className="bg-muted border border-border rounded-xl p-6">
        {step === 'pick' && <ApiPicker onSelect={handleApiSelect} />}
        {step === 'fill' && selectedApi && (
          <CredentialFields
            selectedApi={selectedApi}
            onBack={() => setStep('pick')}
            onSaved={() => navigate('/credentials')}
            editId={id}
            existing={existing}
          />
        )}
        {step === 'fill' && !selectedApi && isEdit && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>
    </div>
  )
}
