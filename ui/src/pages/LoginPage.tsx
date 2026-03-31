import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { JenticLogo } from '../components/ui/Logo'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [searchParams] = useSearchParams()
  const next = searchParams.get('next') || '/'
  
  const loginMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/user/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password })
      })
      if (!res.ok) throw new Error('Login failed')
      return res.json()
    },
    onSuccess: () => {
      window.location.href = next
    }
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-sm p-8 bg-muted rounded-xl border border-border shadow-2xl">
        <div className="flex justify-center mb-8">
          <JenticLogo className="h-12" />
        </div>
        
        <form onSubmit={e => { e.preventDefault(); loginMutation.mutate() }}>
          {loginMutation.isError && (
            <div className="p-3 bg-danger/10 text-danger border border-danger/30 rounded-lg mb-4 text-sm font-semibold">
              Invalid username or password.
            </div>
          )}
          
          <div className="mb-4">
            <label htmlFor="login-username" className="block text-sm font-bold mb-2 text-muted-foreground">Username</label>
            <input 
              id="login-username"
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required 
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden transition-colors" 
            />
          </div>
          
          <div className="mb-8">
            <label htmlFor="login-password" className="block text-sm font-bold mb-2 text-muted-foreground">Password</label>
            <input 
              id="login-password"
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-hidden transition-colors" 
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loginMutation.isPending} 
            className="w-full bg-primary text-background hover:bg-primary-hover font-bold rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
          >
            {loginMutation.isPending ? 'Logging in...' : 'Log In'}
          </button>
        </form>
        
        <p className="mt-6 text-xs text-muted-foreground text-center">
          To reset your password, run <code className="font-mono bg-background px-1">docker exec jentic-mini python3 -m jentic reset-password</code>.
        </p>
      </div>
    </div>
  )
}
