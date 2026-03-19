import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean
  children?: React.ReactNode
  className?: string
}

export function Card({ hoverable, children, className = '', onClick, ...props }: CardProps) {
  return (
    <div
      className={`bg-muted border border-border rounded-xl transition-all ${
        hoverable ? 'cursor-pointer hover:border-primary/50 hover:bg-muted/80' : ''
      } ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`px-5 py-4 border-b border-border ${className}`}>
      {children}
    </div>
  )
}

export function CardBody({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`px-5 py-4 ${className}`}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <h3 className={`font-heading font-semibold text-foreground ${className}`}>
      {children}
    </h3>
  )
}
