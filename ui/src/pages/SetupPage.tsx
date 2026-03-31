import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { UserService } from '../api/generated'
import { AlertTriangle, Check } from 'lucide-react'

/**
 * Setup wizard with two steps:
 *   1. Create admin account
 *   2. Generate agent API key (manual) — OR wait for agent to claim it
 *
 * The `step` state drives which panel is visible.  Health polling only
 * runs during step 2 (waiting-for-agent path) so it cannot interfere
 * with the key display.
 */
type Step = 'account' | 'key'

export default function SetupPage() {
  const [step, setStep] = useState<Step>('account')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [copiedKey, setCopiedKey] = useState(false)

  // ── Step 2: Generate key (declared early so polling can reference it) ──
  const generateKeyMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch('/default-api-key/generate', { method: 'POST', credentials: 'include' })
      if (!r.ok) throw new Error(`Key generation failed (${r.status})`)
      return r.json()
    },
  })

  // Health query — only polls during the key step (waiting for agent)
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health', { credentials: 'include' }).then(r => r.json()),
    refetchInterval: (query) => {
      // Only poll while waiting for an agent to claim the key.
      // Stop polling if the user is generating the key manually.
      if (step !== 'key') return false
      if (generateKeyMutation.data || generateKeyMutation.isPending) return false
      const status = query.state.data?.status
      return status === 'setup_required' ? 3000 : false
    },
  })

  // If health shows everything is already set up AND the user hasn't
  // started the wizard yet, skip straight to the done screen.
  // Once the user has progressed past account creation we trust the
  // step state so health polling can't yank the UI away.
  const alreadySetUp = step === 'account' && health?.status === 'ok'

  // If the account already exists but the key hasn't been claimed yet
  // (e.g. page refresh after account creation), advance to the key step.
  useEffect(() => {
    if (step === 'account' && health?.account_created && health?.status !== 'ok') {
      setStep('key')
    }
  }, [step, health?.account_created, health?.status])

  // ── Step 1: Create account ──────────────────────────────────────────
  const createUserMutation = useMutation({
    mutationFn: () => UserService.createUserUserCreatePost({ requestBody: { username, password } }),
    onSuccess: () => {
      fetch('/user/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password })
      })
        .then(res => {
          if (!res.ok) console.warn('Auto-login failed after account creation:', res.status)
          // Advance to key step regardless — account exists, login can be retried
          setStep('key')
        })
        .catch(() => {
          // Network error — still advance to key step
          setStep('key')
        })
    }
  })

  const createUserError = createUserMutation.error as { status?: number } | null
  const accountAlreadyExists =
    createUserError?.status === 409 || createUserError?.status === 410

  // Agent claimed the key externally (detected via polling).
  // Guard on health being defined to avoid a flash on initial mount.
  const agentClaimedKey = step === 'key' && health != null && health.status !== 'setup_required' && !generateKeyMutation.data

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-md p-8 bg-muted rounded-xl border border-border shadow-2xl">
        <h1 className="text-3xl font-bold mb-6 text-center text-foreground">Welcome to Jentic Mini</h1>

        {/* ── Already set up ── */}
        {alreadySetUp ? (
          <div className="text-center">
            <div className="p-4 bg-success/10 border border-success/30 rounded-lg mb-6 text-success text-sm font-semibold flex items-center justify-center gap-2">
              <Check className="h-4 w-4" /> Setup complete
            </div>
            <button
              onClick={() => window.location.href = '/'}
              className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors"
            >
              Go to Dashboard →
            </button>
          </div>
        ) : null}

        {/* ── Step 1: Create admin account ── */}
        {!alreadySetUp && step === 'account' ? (
          <form onSubmit={e => {
            e.preventDefault()
            createUserMutation.mutate()
          }}>
            <h2 className="text-xl font-semibold mb-4 text-foreground">Create Admin Account</h2>

            {accountAlreadyExists && (
              <div className="mb-4 p-3 bg-warning/10 border border-warning/30 rounded-lg text-warning text-sm">
                An admin account already exists.{' '}
                <a href="/login" className="underline font-semibold">Log in instead →</a>
              </div>
            )}

            {createUserMutation.isError && !accountAlreadyExists && (
              <div className="mb-4 p-3 bg-danger/10 border border-danger/30 rounded-lg text-danger text-sm">
                Something went wrong. Please try again.
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="setup-username" className="block text-sm font-bold mb-2 text-muted-foreground">Username</label>
              <input
                id="setup-username"
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                disabled={accountAlreadyExists}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden transition-colors disabled:opacity-50"
              />
            </div>
            <div className="mb-6">
              <label htmlFor="setup-password" className="block text-sm font-bold mb-2 text-muted-foreground">Password</label>
              <input
                id="setup-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                disabled={accountAlreadyExists}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden transition-colors disabled:opacity-50"
              />
            </div>
            {!accountAlreadyExists && (
              <button
                type="submit"
                disabled={createUserMutation.isPending}
                className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
              >
                {createUserMutation.isPending ? 'Creating...' : 'Create Account'}
              </button>
            )}
          </form>
        ) : null}

        {/* ── Step 2: Agent key ── */}
        {!alreadySetUp && step === 'key' ? (
          <div>
            <div className="p-4 bg-success/10 border border-success/30 rounded-lg mb-6 text-success text-sm font-semibold text-center flex items-center justify-center gap-2">
              <Check className="h-4 w-4" /> Admin account created
            </div>

            {/* Key generated — show it until copied */}
            {generateKeyMutation.data && !copiedKey ? (
              <div className="p-4 bg-danger/10 border border-danger/30 rounded-lg mb-4">
                <div className="text-danger font-bold text-sm mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" /> This key will not be shown again
                </div>
                <div className="font-mono bg-background p-3 rounded text-sm mb-4 break-all text-foreground">
                  {generateKeyMutation.data.key}
                </div>
                <button
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(generateKeyMutation.data.key)
                      setCopiedKey(true)
                    } catch {
                      window.alert('Could not copy to clipboard. Please copy the key manually.')
                    }
                  }}
                  className="w-full bg-primary text-background hover:bg-primary-hover font-semibold py-2 rounded transition-colors"
                >
                  Copy Key
                </button>
              </div>

            /* Key copied — show confirmation + proceed */
            ) : copiedKey ? (
              <div className="text-center">
                <div className="p-4 bg-success/10 border border-success/30 rounded-lg mb-6 text-success text-sm font-semibold flex items-center justify-center gap-2">
                  <Check className="h-4 w-4" /> API key copied
                </div>
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors"
                >
                  Go to Dashboard →
                </button>
              </div>

            /* Agent claimed key externally */
            ) : agentClaimedKey ? (
              <div className="text-center">
                <div className="p-4 bg-success/10 border border-success/30 rounded-lg mb-6 text-success text-sm font-semibold flex items-center justify-center gap-2">
                  <Check className="h-4 w-4" /> Agent claimed the key automatically
                </div>
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors"
                >
                  Go to Dashboard →
                </button>
              </div>

            /* Initial state — generate or wait */
            ) : (
              <>
                <p className="mb-4 text-sm text-muted-foreground">
                  Your AI agent can claim this key automatically. To set it up:
                </p>
                <ol className="mb-4 text-sm text-muted-foreground list-decimal list-inside space-y-1">
                  <li>Install the Jentic skill: <code className="font-mono bg-background px-1 rounded">clawhub install jentic</code></li>
                  <li>Tell your agent the URL of this Jentic Mini instance</li>
                  <li>Your agent will discover and claim the key automatically</li>
                </ol>
                <p className="mb-4 text-sm text-muted-foreground">
                  Alternatively, generate the API key now and give it to your agent manually.
                </p>
                <button
                  onClick={() => generateKeyMutation.mutate()}
                  disabled={generateKeyMutation.isPending}
                  className="w-full bg-primary text-background hover:bg-primary-hover font-semibold rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
                >
                  {generateKeyMutation.isPending ? 'Generating...' : 'Generate Agent API Key'}
                </button>
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
