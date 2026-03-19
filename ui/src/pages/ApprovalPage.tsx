import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { JenticLogo } from '../components/ui/Logo'
import { Button } from '../components/ui/Button'
import { PermissionRuleDisplay } from '../components/ui/PermissionRuleDisplay'
import { Badge } from '../components/ui/Badge'
import type { PermissionRule } from '../api/types'
import { CheckCircle, XCircle, AlertTriangle, Clock, LogIn } from 'lucide-react'

function extractErrorMessage(err: unknown): string {
  if (!err) return 'An unknown error occurred.'
  const e = err as any
  // ApiError: body.detail is FastAPI's standard error field
  if (e?.body?.detail) {
    const detail = e.body.detail
    return typeof detail === 'string' ? detail : JSON.stringify(detail)
  }
  if (e?.status === 401) return 'Not authenticated — please log in first.'
  if (e?.status === 403) return 'You do not have permission to perform this action.'
  if (e?.status === 404) return 'Request not found — it may have already been resolved.'
  if (e?.status === 409) return 'Conflict — the request may have already been acted on.'
  if (e?.statusText) return `${e.status}: ${e.statusText}`
  // Only use .message if it's a real string, not "[object Object]"
  if (e?.message && typeof e.message === 'string' && !e.message.includes('[object')) return e.message
  return `Unexpected error (HTTP ${e?.status ?? '?'})`
}

export default function ApprovalPage() {
  const { toolkit_id, req_id } = useParams<{ toolkit_id: string; req_id: string }>()
  const navigate = useNavigate()
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<'approved' | 'denied' | null>(null)

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ['user-me'],
    queryFn: api.getMe,
    retry: false,
  })

  const isLoggedIn = user?.logged_in === true

  const { data: request, isLoading: requestLoading, error: requestError } = useQuery({
    queryKey: ['access-request', toolkit_id, req_id],
    queryFn: () => api.getAccessRequest(toolkit_id!, req_id!),
    enabled: !!toolkit_id && !!req_id && isLoggedIn,
    retry: false,
  })

  const { data: toolkit } = useQuery({
    queryKey: ['toolkit', toolkit_id],
    queryFn: () => api.getToolkit(toolkit_id!),
    enabled: !!toolkit_id && isLoggedIn,
    retry: false,
  })

  const approveMutation = useMutation({
    mutationFn: () => api.approveAccessRequest(toolkit_id!, req_id!),
    onSuccess: () => {
      setResult('approved')
      setTimeout(() => navigate('/toolkits'), 2500)
    },
  })

  const denyMutation = useMutation({
    mutationFn: () => api.denyAccessRequest(toolkit_id!, req_id!),
    onSuccess: () => {
      setResult('denied')
      setTimeout(() => navigate('/toolkits'), 2500)
    },
  })

  const actionError = approveMutation.error || denyMutation.error

  // ── Loading user ──────────────────────────────────────────────────────────
  if (userLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  // ── Not logged in ─────────────────────────────────────────────────────────
  if (!isLoggedIn) {
    const loginUrl = `/login?next=${encodeURIComponent(window.location.pathname)}`
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <div className="border-b border-border px-6 py-4">
          <JenticLogo />
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-md w-full text-center space-y-5">
            <LogIn className="h-12 w-12 text-primary mx-auto" />
            <div className="space-y-2">
              <h1 className="font-heading text-xl font-bold text-foreground">Login Required</h1>
              <p className="text-muted-foreground">
                You need to be logged in as an admin to approve or deny access requests.
              </p>
            </div>
            <Button onClick={() => navigate(loginUrl)} className="w-full">
              <LogIn className="h-4 w-4 mr-2" />
              Log In to Continue
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // ── Loading request ───────────────────────────────────────────────────────
  if (requestLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading request...</div>
      </div>
    )
  }

  // ── Request error or not found ────────────────────────────────────────────
  if (requestError || !request) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-warning mx-auto" />
          <h1 className="font-heading text-xl font-bold text-foreground">Request Not Found</h1>
          <p className="text-muted-foreground">
            {requestError
              ? extractErrorMessage(requestError)
              : "This access request doesn't exist or the link may have expired."}
          </p>
          <Button onClick={() => navigate('/toolkits')}>Go to Toolkits</Button>
        </div>
      </div>
    )
  }

  // ── Already resolved ──────────────────────────────────────────────────────
  if (request.status !== 'pending') {
    const isApproved = request.status === 'approved'
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-4">
          {isApproved
            ? <CheckCircle className="h-12 w-12 text-success mx-auto" />
            : <XCircle className="h-12 w-12 text-danger mx-auto" />
          }
          <h1 className="font-heading text-xl font-bold text-foreground">
            Request Already {isApproved ? 'Approved' : 'Denied'}
          </h1>
          <p className="text-muted-foreground">
            This access request was already {request.status}.
          </p>
          <Button onClick={() => navigate('/toolkits')}>Go to Toolkits</Button>
        </div>
      </div>
    )
  }

  // ── After action success ──────────────────────────────────────────────────
  if (result) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-4">
          {result === 'approved'
            ? <CheckCircle className="h-12 w-12 text-success mx-auto" />
            : <XCircle className="h-12 w-12 text-danger mx-auto" />
          }
          <h1 className="font-heading text-xl font-bold text-foreground">
            Request {result === 'approved' ? 'Approved' : 'Denied'}
          </h1>
          <p className="text-muted-foreground">Redirecting to toolkits...</p>
        </div>
      </div>
    )
  }

  const payload = request.payload as Record<string, unknown>
  const requestedCredId = payload?.credential_id as string | undefined
  const requestedApiId = payload?.api_id as string | undefined
  const requestedRules = payload?.rules as PermissionRule[] | undefined

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Minimal header */}
      <div className="border-b border-border px-6 py-4">
        <JenticLogo />
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-2xl w-full space-y-6">
          {/* Title */}
          <div className="text-center space-y-2">
            <div className="flex items-center justify-center gap-2">
              <Clock className="h-6 w-6 text-warning" />
              <h1 className="font-heading text-2xl font-bold text-foreground">Access Request Pending</h1>
            </div>
            <p className="text-muted-foreground">Review the details and approve or deny.</p>
          </div>

          {/* Request card */}
          <div className="bg-muted border border-border rounded-xl p-6 space-y-5">
            {/* Toolkit */}
            <div>
              <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-1">Toolkit</p>
              <div className="flex items-center gap-2">
                <span className="font-heading font-semibold text-foreground">{toolkit?.name ?? toolkit_id}</span>
                {toolkit?.simulate && <Badge variant="default">simulate</Badge>}
              </div>
            </div>

            {/* Type */}
            <div>
              <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-1">Request Type</p>
              <Badge variant={request.type === 'grant' ? 'default' : 'warning'} className="text-sm">
                {request.type === 'grant' ? '🔐 Credential Access' : '🔒 Permission Modification'}
              </Badge>
            </div>

            {/* Reason */}
            {request.reason && (
              <div>
                <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-1">Agent says</p>
                <p className="text-foreground bg-background border border-border rounded-lg p-3 text-sm italic">
                  "{request.reason}"
                </p>
              </div>
            )}

            {/* Description */}
            {request.description && (
              <div>
                <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-1">Description</p>
                <p className="text-foreground text-sm">{request.description}</p>
              </div>
            )}

            {/* Grant details */}
            {request.type === 'grant' && (requestedCredId || requestedApiId) && (
              <div>
                <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-2">Requesting Access To</p>
                <div className="bg-background border border-border rounded-lg p-3 space-y-1">
                  {requestedCredId && (
                    <p className="text-sm text-foreground">
                      <span className="text-muted-foreground">Credential:</span>{' '}
                      <code className="font-mono text-accent-teal">{requestedCredId}</code>
                    </p>
                  )}
                  {requestedApiId && (
                    <p className="text-sm text-foreground">
                      <span className="text-muted-foreground">API:</span>{' '}
                      <code className="font-mono text-accent-blue">{requestedApiId}</code>
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Permission changes */}
            {request.type === 'modify_permissions' && requestedRules && requestedRules.length > 0 && (
              <div>
                <p className="text-xs font-mono uppercase tracking-widest text-primary/60 mb-2">Requested Permission Changes</p>
                <div className="bg-background border border-border rounded-lg p-4">
                  <PermissionRuleDisplay rules={requestedRules} />
                </div>
              </div>
            )}

            {request.created_at && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-2 border-t border-border">
                <Clock className="h-3 w-3" />
                <span>Requested {new Date(request.created_at * 1000).toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Action error — now with meaningful messages */}
          {actionError && (
            <div className="flex items-start gap-2 text-sm text-danger bg-danger/10 border border-danger/30 rounded-lg p-3">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{extractErrorMessage(actionError)}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button
              onClick={() => { setProcessing(true); approveMutation.mutate() }}
              loading={approveMutation.isPending}
              disabled={processing}
              className="flex-1 py-3 text-base"
            >
              <CheckCircle className="h-5 w-5 mr-2" />
              Approve Request
            </Button>
            <Button
              onClick={() => { setProcessing(true); denyMutation.mutate() }}
              loading={denyMutation.isPending}
              disabled={processing}
              variant="danger"
              className="flex-1 py-3 text-base"
            >
              <XCircle className="h-5 w-5 mr-2" />
              Deny Request
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
