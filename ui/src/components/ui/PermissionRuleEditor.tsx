import { Plus, Trash2 } from 'lucide-react';
import { Button } from './Button';
import type { PermissionRule } from '@/api/types';

interface PermissionRuleEditorProps {
	rules: PermissionRule[];
	onChange: (rules: PermissionRule[]) => void;
}

const emptyRule = (): PermissionRule => ({ effect: 'allow', path: '', methods: [] });

export function PermissionRuleEditor({ rules, onChange }: PermissionRuleEditorProps) {
	const addRule = () => onChange([...rules, emptyRule()]);
	const removeRule = (i: number) => onChange(rules.filter((_, idx) => idx !== i));
	const updateRule = (i: number, patch: Partial<PermissionRule>) => {
		const updated = rules.map((r, idx) => (idx === i ? { ...r, ...patch } : r));
		onChange(updated);
	};

	return (
		<div className="space-y-2">
			{rules.map((rule, i) => (
				<div
					key={i}
					className="bg-background border-border flex items-start gap-2 rounded-lg border p-3"
				>
					{/* Effect */}
					<select
						value={rule.effect}
						onChange={(e) =>
							updateRule(i, { effect: e.target.value as 'allow' | 'deny' })
						}
						className="bg-muted border-border text-foreground rounded border px-2 py-1 text-sm focus:outline-hidden"
					>
						<option value="allow">Allow</option>
						<option value="deny">Deny</option>
					</select>

					{/* Path */}
					<input
						type="text"
						value={rule.path ?? ''}
						onChange={(e) => updateRule(i, { path: e.target.value || null })}
						placeholder="/path/prefix or *"
						className="bg-muted border-border text-foreground focus:border-primary flex-1 rounded border px-2 py-1 font-mono text-sm focus:outline-hidden"
					/>

					{/* Methods */}
					<input
						type="text"
						value={rule.methods?.join(', ') ?? ''}
						onChange={(e) =>
							updateRule(i, {
								methods: e.target.value
									? e.target.value
											.split(',')
											.map((s) => s.trim().toUpperCase())
											.filter(Boolean)
									: null,
							})
						}
						placeholder="GET, POST (blank=any)"
						className="bg-muted border-border text-foreground focus:border-primary w-40 rounded border px-2 py-1 font-mono text-sm focus:outline-hidden"
					/>

					<button
						type="button"
						onClick={() => removeRule(i)}
						className="text-danger hover:text-danger/80 mt-1 shrink-0"
					>
						<Trash2 className="h-4 w-4" />
					</button>
				</div>
			))}

			<Button type="button" variant="secondary" size="sm" onClick={addRule}>
				<Plus className="mr-1 h-4 w-4" /> Add Rule
			</Button>
		</div>
	);
}
