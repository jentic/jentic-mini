import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Copy, CheckCircle, AlertTriangle } from 'lucide-react'
import { Button } from './Button'

interface OneTimeKeyDisplayProps {
  keyValue: string
  onConfirm: () => void
  title?: string
}

export function OneTimeKeyDisplay({ keyValue, onConfirm, title }: OneTimeKeyDisplayProps) {
  const [copied, setCopied] = useState(false)
  const [confirmed, setConfirmed] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(keyValue)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="border-2 border-danger/40 rounded-xl p-5 space-y-4 bg-danger/5">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-danger">{title ?? 'API Key Generated'}</p>
          <p className="text-sm text-muted-foreground mt-1">
            This key will <strong className="text-foreground">never be shown again</strong>.
            Copy it now and store it securely before dismissing.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <code className="flex-1 bg-background border border-border rounded-lg px-4 py-3 font-mono text-sm text-foreground break-all">
          {keyValue}
        </code>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCopy}
          className="shrink-0"
        >
          {copied
            ? <><CheckCircle className="h-4 w-4 text-success" /> Copied</>
            : <><Copy className="h-4 w-4" /> Copy</>
          }
        </Button>
      </div>

      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={e => setConfirmed(e.target.checked)}
          className="rounded border-border h-4 w-4"
        />
        <span className="text-sm text-foreground">I've copied this key to a safe place</span>
      </label>

      <Button
        onClick={onConfirm}
        disabled={!confirmed}
        className="w-full"
      >
        Done — dismiss
      </Button>
    </div>
  )
}
