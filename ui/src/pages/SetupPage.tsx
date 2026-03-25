import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { UserService } from '../api/generated'

export default function SetupPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [copiedKey, setCopiedKey] = useState(false)

  const { data: health, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health', { credentials: 'include' }).then(r => r.json()),
    // Poll while waiting for agent to claim the key
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'setup_required' ? 3000 : false
    },
  })

  const generateKeyMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch('/default-api-key/generate', { method: 'POST', credentials: 'include' })
      if (!r.ok) throw new Error(`Key generation failed (${r.status})`)
      return r.json()
    },
    onSuccess: () => refetchHealth(),
  })

  const createUserMutation = useMutation({
    mutationFn: () => UserService.createUserUserCreatePost({ requestBody: { username, password } }),
    onSuccess: () => {
      // Auto-login after creating user
      fetch('/user/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password })
      }).then(() => window.location.href = '/')
    }
  })

  // Account already exists and agent key still unclaimed — waiting state
  const accountCreated = health?.account_created || createUserMutation.isSuccess
  const keyUnclaimed = health?.status === 'setup_required'
  const waitingForAgent = accountCreated && keyUnclaimed

  // Error from createUser: 409 or 410 means account already exists
  const createUserError = createUserMutation.error as { status?: number } | null
  const accountAlreadyExists =
    createUserError?.status === 409 || createUserError?.status === 410

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-md p-8 bg-muted rounded-xl border border-border shadow-2xl">
        <h1 className="text-3xl font-bold mb-6 text-center text-foreground">Welcome to Jentic Mini</h1>

        {/* Step 1: Generate / show agent key */}
        {health?.status === 'setup_required' ? (
          <div className="mb-6">
            <p className="mb-1 text-sm font-semibold text-foreground">Step 1 — Connect your agent</p>
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
            {!generateKeyMutation.data ? (
              <button
                onClick={() => generateKeyMutation.mutate()}
                disabled={generateKeyMutation.isPending}
                className="w-full bg-primary text-background hover:bg-primary-hover font-semibold rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
              >
                {generateKeyMutation.isPending ? 'Generating...' : 'Generate Agent API Key'}
              </button>
            ) : (
              <div className="p-4 bg-danger/10 border border-danger/30 rounded-lg">
                <div className="text-danger font-bold text-sm mb-2 flex items-center gap-2">
                  ⚠️ This key will not be shown again
                </div>
                <div className="font-mono bg-background p-3 rounded text-sm mb-4 break-all text-foreground">
                  {generateKeyMutation.data.key}
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(generateKeyMutation.data.key)
                    setCopiedKey(true)
                  }}
                  className={`w-full font-semibold py-2 rounded transition-colors ${
                    copiedKey
                      ? 'bg-success/20 text-success border border-success/30'
                      : 'bg-primary text-background hover:bg-primary-hover'
                  }`}
                >
                  {copiedKey ? '✓ Copied to clipboard' : 'Copy Key'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 bg-success/10 border border-success/30 rounded-lg mb-6 text-success text-sm font-semibold text-center">
            Agent API key claimed ✓
          </div>
        )}

        {/* Step 2: Create admin account — or waiting state */}
        {waitingForAgent ? (
          <div className="p-4 bg-muted border border-border rounded-lg text-center">
            <p className="text-sm font-semibold text-foreground mb-1">Admin account created ✓</p>
            <p className="text-sm text-muted-foreground">
              Waiting for your agent to claim its API key…
            </p>
            <div className="mt-3 flex justify-center">
              <span className="inline-block w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Make sure your agent has the Jentic skill installed and knows this instance's URL.
            </p>
          </div>
        ) : (
          <form onSubmit={e => {
            e.preventDefault()
            if (!health?.default_key_claimed && !copiedKey && generateKeyMutation.data) {
              alert("Please copy your agent API key first.")
              return
            }
            createUserMutation.mutate()
          }}>
            <h2 className="text-xl font-semibold mb-4 text-foreground">
              {health?.status === 'setup_required' ? 'Step 2 — ' : ''}Create Admin Account
            </h2>

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
              <label className="block text-sm font-bold mb-2 text-muted-foreground">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                disabled={accountAlreadyExists}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none transition-colors disabled:opacity-50"
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm font-bold mb-2 text-muted-foreground">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                disabled={accountAlreadyExists}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none transition-colors disabled:opacity-50"
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
        )}
      </div>
    </div>
  )
}
