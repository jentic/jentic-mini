import { Plus, Trash2 } from 'lucide-react';
import { Button } from './Button';
import { Input } from './Input';
import { Select } from './Select';
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
					<Select
						value={rule.effect}
						onChange={(e) =>
							updateRule(i, { effect: e.target.value as 'allow' | 'deny' })
						}
					>
						<option value="allow">Allow</option>
						<option value="deny">Deny</option>
					</Select>

					{/* Path */}
					<Input
						type="text"
						value={rule.path ?? ''}
						onChange={(e) => updateRule(i, { path: e.target.value || null })}
						placeholder="/path/prefix or *"
						className="flex-1 font-mono"
					/>

					{/* Methods */}
					<Input
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
						className="w-40 font-mono"
					/>

					<Button
						variant="ghost"
						size="icon"
						onClick={() => removeRule(i)}
						aria-label="Remove rule"
						className="text-danger hover:text-danger/80 mt-1 shrink-0"
					>
						<Trash2 className="h-4 w-4" />
					</Button>
				</div>
			))}

			<Button type="button" variant="secondary" size="sm" onClick={addRule}>
				<Plus className="mr-1 h-4 w-4" /> Add Rule
			</Button>
		</div>
	);
}
