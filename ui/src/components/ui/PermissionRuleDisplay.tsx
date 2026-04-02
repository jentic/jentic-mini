import { Lock, ShieldCheck, ShieldX } from 'lucide-react';
import type { PermissionRule } from '@/api/types';

function describeRule(rule: PermissionRule): string {
	const parts: string[] = [];

	if (rule._system) {
		return 'System rule (managed automatically)';
	}

	const effect = rule.effect === 'allow' ? 'Allow' : 'Deny';

	if (rule.operations && rule.operations.length > 0) {
		parts.push(`${effect} operations: ${rule.operations.join(', ')}`);
	} else if (rule.path) {
		const methods =
			rule.methods && rule.methods.length > 0 ? rule.methods.join(', ') : 'any method';
		parts.push(`${effect} ${methods} requests to ${rule.path}`);
	} else {
		parts.push(`${effect} all requests`);
	}

	return parts.join(' — ');
}

interface PermissionRuleDisplayProps {
	rules: PermissionRule[];
}

export function PermissionRuleDisplay({ rules }: PermissionRuleDisplayProps) {
	if (!rules || rules.length === 0) {
		return (
			<p className="text-muted-foreground text-sm italic">No permission rules configured.</p>
		);
	}

	return (
		<ul className="space-y-2">
			{rules.map((rule, i) => {
				const isSystem = rule._system === true;
				const isAllow = rule.effect === 'allow';
				return (
					<li
						key={i}
						className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${
							isSystem
								? 'bg-primary/5 text-muted-foreground'
								: isAllow
									? 'bg-success/5 text-foreground'
									: 'bg-danger/5 text-foreground'
						}`}
					>
						<span className="mt-0.5 shrink-0">
							{isSystem ? (
								<Lock className="text-muted-foreground h-4 w-4" />
							) : isAllow ? (
								<ShieldCheck className="text-success h-4 w-4" />
							) : (
								<ShieldX className="text-danger h-4 w-4" />
							)}
						</span>
						<span>{describeRule(rule)}</span>
					</li>
				);
			})}
		</ul>
	);
}
