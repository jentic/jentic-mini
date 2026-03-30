import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge, MethodBadge, StatusBadge } from '../../components/ui/Badge'

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge>active</Badge>)
    expect(screen.getByText('active')).toBeInTheDocument()
  })

  it('renders with each variant without crashing', () => {
    const variants = ['default', 'success', 'warning', 'danger', 'pending'] as const
    for (const variant of variants) {
      const { unmount } = render(<Badge variant={variant}>{variant}</Badge>)
      expect(screen.getByText(variant)).toBeInTheDocument()
      unmount()
    }
  })
})

describe('MethodBadge', () => {
  it('renders the HTTP method in uppercase', () => {
    render(<MethodBadge method="get" />)
    expect(screen.getByText('GET')).toBeInTheDocument()
  })

  it('shows "?" when method is null', () => {
    render(<MethodBadge method={null} />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })

  it('shows "?" when method is undefined', () => {
    render(<MethodBadge />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })
})

describe('StatusBadge', () => {
  it('renders the status code', () => {
    render(<StatusBadge status={200} />)
    expect(screen.getByText('200')).toBeInTheDocument()
  })

  it('returns null for falsy status', () => {
    const { container } = render(<StatusBadge status={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('returns null for zero status', () => {
    const { container } = render(<StatusBadge status={0} />)
    expect(container).toBeEmptyDOMElement()
  })
})
