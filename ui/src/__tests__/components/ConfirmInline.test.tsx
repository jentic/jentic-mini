import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmInline } from '../../components/ui/ConfirmInline'

describe('ConfirmInline', () => {
  it('renders the trigger element initially', () => {
    render(
      <ConfirmInline onConfirm={() => {}} message="Are you sure?">
        <button>Delete</button>
      </ConfirmInline>
    )
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
    expect(screen.queryByText('Are you sure?')).not.toBeInTheDocument()
  })

  it('shows confirmation message and buttons on trigger click', () => {
    render(
      <ConfirmInline onConfirm={() => {}} message="Are you sure?">
        <button>Delete</button>
      </ConfirmInline>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('calls onConfirm when confirm is clicked', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmInline onConfirm={onConfirm} message="Delete this?">
        <button>Delete</button>
      </ConfirmInline>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('reverts to trigger when cancel is clicked', () => {
    render(
      <ConfirmInline onConfirm={() => {}} message="Delete this?">
        <button>Delete</button>
      </ConfirmInline>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
    expect(screen.queryByText('Delete this?')).not.toBeInTheDocument()
  })

  it('uses custom confirm label', () => {
    render(
      <ConfirmInline onConfirm={() => {}} message="Really?" confirmLabel="Yes, delete">
        <button>Remove</button>
      </ConfirmInline>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(screen.getByRole('button', { name: 'Yes, delete' })).toBeInTheDocument()
  })

  it('stops event propagation on trigger click', () => {
    const outerClick = vi.fn()
    render(
      <div onClick={outerClick}>
        <ConfirmInline onConfirm={() => {}} message="Sure?">
          <button>Delete</button>
        </ConfirmInline>
      </div>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(outerClick).not.toHaveBeenCalled()
  })
})
