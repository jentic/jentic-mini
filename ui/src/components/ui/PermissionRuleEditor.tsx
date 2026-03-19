import type { PermissionRule } from '../../api/types'
import { Button } from './Button'
import { Plus, Trash2 } from 'lucide-react'

interface PermissionRuleEditorProps {
  rules: PermissionRule[]
  onChange: (rules: PermissionRule[]) => void
}

const emptyRule = (): PermissionRule => ({ effect: 'allow', path: '', methods: [] })

export function PermissionRuleEditor({ rules, onChange }: PermissionRuleEditorProps) {
  const addRule = () => onChange([...rules, emptyRule()])
  const removeRule = (i: number) => onChange(rules.filter((_, idx) => idx !== i))
  const updateRule = (i: number, patch: Partial<PermissionRule>) => {
    const updated = rules.map((r, idx) => idx === i ? { ...r, ...patch } : r)
    onChange(updated)
  }

  return (
    <div className="space-y-2">
      {rules.map((rule, i) => (
        <div key={i} className="flex gap-2 items-start p-3 bg-background border border-border rounded-lg">
          {/* Effect */}
          <select
            value={rule.effect}
            onChange={e => updateRule(i, { effect: e.target.value as 'allow' | 'deny' })}
            className="bg-muted border border-border rounded px-2 py-1 text-sm text-foreground focus:outline-none"
          >
            <option value="allow">✅ Allow</option>
            <option value="deny">❌ Deny</option>
          </select>

          {/* Path */}
          <input
            type="text"
            value={rule.path ?? ''}
            onChange={e => updateRule(i, { path: e.target.value || null })}
            placeholder="/path/prefix or *"
            className="flex-1 bg-muted border border-border rounded px-2 py-1 text-sm text-foreground font-mono focus:border-primary focus:outline-none"
          />

          {/* Methods */}
          <input
            type="text"
            value={rule.methods?.join(', ') ?? ''}
            onChange={e => updateRule(i, {
              methods: e.target.value ? e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean) : null
            })}
            placeholder="GET, POST (blank=any)"
            className="w-40 bg-muted border border-border rounded px-2 py-1 text-sm text-foreground font-mono focus:border-primary focus:outline-none"
          />

          <button
            onClick={() => removeRule(i)}
            className="text-danger hover:text-danger/80 shrink-0 mt-1"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ))}

      <Button type="button" variant="secondary" size="sm" onClick={addRule}>
        <Plus className="h-4 w-4 mr-1" /> Add Rule
      </Button>
    </div>
  )
}
