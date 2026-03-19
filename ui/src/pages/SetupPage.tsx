import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { UserService } from '../api/generated'

export default function SetupPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [copiedKey, setCopiedKey] = useState(false)
  
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/health', { credentials: 'include' }).then(r => r.json())
  })

  const generateKeyMutation = useMutation({
    mutationFn: () => fetch('/default-api-key/generate', { method: 'POST', credentials: 'include' }).then(r => r.json()),
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-md p-8 bg-muted rounded-xl border border-border shadow-2xl">
        <h1 className="text-3xl font-bold mb-6 text-center text-foreground">Welcome to Jentic Mini</h1>

        {health?.default_key_claimed === false ? (
          <div className="mb-6">
            <p className="mb-4 text-sm text-muted-foreground">First, generate your default agent API key:</p>
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
            Agent API key generated ✓
          </div>
        )}

        <form onSubmit={e => {
          e.preventDefault()
          if (!health?.default_key_claimed && !copiedKey && generateKeyMutation.data) {
            alert("Please copy your agent API key first.")
            return
          }
          createUserMutation.mutate()
        }}>
          <h2 className="text-xl font-semibold mb-4 text-foreground">Create Admin Account</h2>
          <div className="mb-4">
            <label className="block text-sm font-bold mb-2 text-muted-foreground">Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required 
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none transition-colors" 
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-bold mb-2 text-muted-foreground">Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none transition-colors" 
            />
          </div>
          <button 
            type="submit" 
            disabled={createUserMutation.isPending} 
            className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
          >
            {createUserMutation.isPending ? 'Creating...' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
