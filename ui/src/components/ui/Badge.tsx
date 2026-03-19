import React from 'react'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'pending'

const variantClasses: Record<Variant, string> = {
  default:  'bg-primary/10 text-primary border-primary/20',
  success:  'bg-success/10 text-success border-success/20',
  warning:  'bg-warning/10 text-warning border-warning/20',
  danger:   'bg-danger/10 text-danger border-danger/20',
  pending:  'bg-accent-orange/10 text-accent-orange border-accent-orange/20',
}

interface BadgeProps {
  variant?: Variant
  children: React.ReactNode
  className?: string
}

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono border ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  )
}

const methodColors: Record<string, string> = {
  GET:    'bg-accent-teal/10 text-accent-teal border-accent-teal/30',
  POST:   'bg-accent-blue/10 text-accent-blue border-accent-blue/30',
  PUT:    'bg-accent-orange/10 text-accent-orange border-accent-orange/30',
  PATCH:  'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30',
  DELETE: 'bg-danger/10 text-danger border-danger/30',
}

export function MethodBadge({ method }: { method?: string | null }) {
  const m = method?.toUpperCase() ?? '?'
  const colors = methodColors[m] ?? 'bg-muted text-muted-foreground border-border'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono font-bold border ${colors} w-14 text-center`}>
      {m}
    </span>
  )
}

export function StatusBadge({ status }: { status?: number | null }) {
  if (!status) return null
  const variant: Variant =
    status >= 500 ? 'danger' :
    status >= 400 ? 'warning' :
    status >= 200 && status < 300 ? 'success' : 'default'
  return <Badge variant={variant}>{status}</Badge>
}
