import React from 'react';
import { cn } from '@/lib/utils';

export type Variant = 'default' | 'success' | 'warning' | 'danger' | 'pending';

const variantClasses: Record<Variant, string> = {
	default: 'bg-primary/10 text-primary border-primary/20',
	success: 'bg-success/10 text-success border-success/20',
	warning: 'bg-warning/10 text-warning border-warning/20',
	danger: 'bg-danger/10 text-danger border-danger/20',
	pending: 'bg-accent-orange/10 text-accent-orange border-accent-orange/20',
};

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
	variant?: Variant;
}

export function Badge({ variant = 'default', children, className, ...props }: BadgeProps) {
	return (
		<span
			className={cn(
				'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs',
				variantClasses[variant],
				className,
			)}
			{...props}
		>
			{children}
		</span>
	);
}

const methodColors: Record<string, string> = {
	GET: 'bg-accent-teal/10 text-accent-teal border-accent-teal/30',
	POST: 'bg-accent-blue/10 text-accent-blue border-accent-blue/30',
	PUT: 'bg-accent-orange/10 text-accent-orange border-accent-orange/30',
	PATCH: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/30',
	DELETE: 'bg-danger/10 text-danger border-danger/30',
};

export function MethodBadge({ method }: { method?: string | null }) {
	const m = method?.toUpperCase() ?? '?';
	const colors = methodColors[m] ?? 'bg-muted text-muted-foreground border-border';
	return (
		<span
			className={cn(
				'inline-block w-14 rounded border px-1.5 py-0.5 text-center font-mono text-[10px] font-bold',
				colors,
			)}
		>
			{m}
		</span>
	);
}

export function StatusBadge({ status }: { status?: number | null }) {
	if (!status) return null;
	const variant: Variant =
		status >= 500
			? 'danger'
			: status >= 400
				? 'warning'
				: status >= 200 && status < 300
					? 'success'
					: 'default';
	return <Badge variant={variant}>{status}</Badge>;
}
