import type { PermissionRule } from '../../api/types'
import { Lock, ShieldCheck, ShieldX } from 'lucide-react'

function describeRule(rule: PermissionRule): string {
  const parts: string[] = []

  if (rule._system) {
    return 'System rule (managed automatically)'
  }

  const effect = rule.effect === 'allow' ? 'Allow' : 'Deny'

  if (rule.operations && rule.operations.length > 0) {
    parts.push(`${effect} operations: ${rule.operations.join(', ')}`)
  } else if (rule.path) {
    const methods = rule.methods && rule.methods.length > 0
      ? rule.methods.join(', ')
      : 'any method'
    parts.push(`${effect} ${methods} requests to ${rule.path}`)
  } else {
    parts.push(`${effect} all requests`)
  }

  return parts.join(' — ')
}

interface PermissionRuleDisplayProps {
  rules: PermissionRule[]
}

export function PermissionRuleDisplay({ rules }: PermissionRuleDisplayProps) {
  if (!rules || rules.length === 0) {
    return <p className="text-sm text-muted-foreground italic">No permission rules configured.</p>
  }

  return (
    <ul className="space-y-2">
      {rules.map((rule, i) => {
        const isSystem = rule._system === true
        const isAllow = rule.effect === 'allow'
        return (
          <li
            key={i}
            className={`flex items-start gap-2 text-sm rounded-lg px-3 py-2 ${
              isSystem
                ? 'bg-primary/5 text-muted-foreground'
                : isAllow
                ? 'bg-success/5 text-foreground'
                : 'bg-danger/5 text-foreground'
            }`}
          >
            <span className="shrink-0 mt-0.5">
              {isSystem ? <Lock className="h-4 w-4 text-muted-foreground" /> : isAllow ? <ShieldCheck className="h-4 w-4 text-success" /> : <ShieldX className="h-4 w-4 text-danger" />}
            </span>
            <span>{describeRule(rule)}</span>
          </li>
        )
      })}
    </ul>
  )
}
