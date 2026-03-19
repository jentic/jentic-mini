import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

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
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="21.5 25.4 265.8 66.8" fill="currentColor" className="h-10 text-primary">
            <g>
              <path d="M94.04,26.63c-2.28-.32-4.91,2.9-7.17,8.67-2.61,6.68-5.26,13.38-8.06,19.87l-.03.06-1.57,3.69h0s-.05.13-.05.13c-1.16,2.74-5,11.78-6.24,14.68-.82,1.94-1.7,3.8-2.65,5.59,0,0,0,0,0,.01h0s-.01.02-.02.03c-.65,1.24-1.37,2.39-2.15,3.4-5.36,6.93-12.54,8.78-17.79,9.07-7.89.13-18.36-3.07-22.73-14.86-2.07-5.36-2.58-11.83-2.41-18.05h36.34s-1.47,3.37-1.47,3.37l-.3.69-3.06.08c-2.66.07-5.24.04-7.93.16-2.38.11-4.62-.08-6.49,2.04-.74.84-1.23,1.86-1.49,2.95-.35,1.51-.15,2.63.59,4.45,1.52,3.38,4.63,5.4,8.33,5.4.11,0,.23,0,.34,0,2.09-.07,4.28-.8,6.08-2.14,1.59-1.19,2.78-3.02,3.71-5.05l2.33-5.85,14.87-35.07h0s0-.01,0-.01c.38-.96.76-1.92,1.14-2.88,0-.01,0-.02.01-.03.68-1.66,1.45-1.67,1.46-1.67,0,0,2.45-.61,7.67-.61,4.68,0,7.92.42,8.06.51.13.09.66.16.65,1.39Z" fill="currentColor" stroke="none"/>
              <path d="M104.8,58.91h-.03l-1.96-6.2-.02-.06-2.06-6.51h0s-3.83-12.16-3.83-12.16c-.72-2.15-1.34-4.39-3.11-4.01-3.1.68-4.9,5.86-6.39,9.94-.36.97-.73,2.03-.93,3.16l.47.58,12.4,15.26.14.17h-16.88l-2.38-.02-.02.05-1.41,3.24-.3.7h27.65l-1.33-4.14Z" fill="currentColor" stroke="none"/>
            </g>
            <g>
              <path d="M131.94,42.2l-2.54,7.93h11.36l.18.13c.32.23.43.45.43.83,0,2.45-.03,4.94-.06,7.14-.04,3.04-.09,6.48-.03,9.76v.08c-.42,4.55-4.35,7-7.83,7-2.79,0-5.14-1.52-6.28-4.08-1.23-2.75-.34-5.18.58-6.99l.4-.78h-8.57l-.14.34c-1.35,3.39-1.32,7.17.1,10.64,1.53,3.76,4.56,6.73,8.31,8.15,1.82.69,3.71,1.04,5.61,1.04,4.1,0,8.07-1.61,11.18-4.52,3.14-2.94,5.04-6.9,5.34-11.15v-.02s0-25.5,0-25.5h-18.01Z" fill="currentColor" stroke="none"/>
              <path d="M177.07,53.63c-2.15-1.41-4.8-2.11-7.93-2.11-2.39,0-4.51.42-6.38,1.26-1.87.84-3.44,1.97-4.7,3.39-1.26,1.42-2.23,3.04-2.88,4.83-.66,1.8-.99,3.68-.99,5.63v1.07c0,1.89.33,3.73.99,5.53.66,1.8,1.63,3.43,2.91,4.89,1.28,1.46,2.87,2.62,4.78,3.47,1.9.85,4.1,1.28,6.6,1.28s4.63-.44,6.52-1.31c1.89-.87,3.45-2.07,4.7-3.61,1.25-1.53,2.08-3.28,2.51-5.23h-7.85c-.36.89-1.03,1.64-2.03,2.24-1,.61-2.28.91-3.85.91-1.71,0-3.10-.36-4.17-1.07-1.07-.71-1.85-1.72-2.35-3.02-.28-.72-.47-1.52-.6-2.38h21.37v-2.88c0-2.67-.57-5.14-1.71-7.40-1.14-2.26-2.79-4.09-4.94-5.50Z" fill="currentColor" stroke="none"/>
              <path d="M249.95,49.65c-1.6,0-2.79-.42-3.55-1.26-.77-.84-1.15-1.9-1.15-3.18s.38-2.39,1.15-3.23c.77-.84,1.95-1.26,3.55-1.26s2.79.42,3.55,1.26c.77.84,1.15,1.91,1.15,3.23s-.38,2.34-1.15,3.18c-.77.84-1.95,1.26-3.55,1.26Z" fill="currentColor" stroke="none"/>
              <path d="M255.18,52.53h-8.6v29.27h8.6v-29.27Z" fill="currentColor" stroke="none"/>
            </g>
          </svg>
          <span className="text-xs font-mono text-accent-teal/70 ml-2 mt-5 border border-accent-teal/30 px-2 py-0.5 rounded-full">Mini</span>
        </div>
        
        <form onSubmit={e => { e.preventDefault(); loginMutation.mutate() }}>
          {loginMutation.isError && (
            <div className="p-3 bg-danger/10 text-danger border border-danger/30 rounded-lg mb-4 text-sm font-semibold">
              Invalid username or password.
            </div>
          )}
          
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
          
          <div className="mb-8">
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
