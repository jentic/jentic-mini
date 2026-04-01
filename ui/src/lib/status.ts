import type { Variant } from '@/components/ui/Badge';

export function statusVariant(status: string | null | undefined): Variant {
	if (!status) return 'default';
	const s = status.toLowerCase();
	if (['success', 'completed', 'ok', 'active'].includes(s)) return 'success';
	if (['failed', 'error', 'rejected', 'denied'].includes(s)) return 'danger';
	if (['warning', 'timeout'].includes(s)) return 'warning';
	if (['pending', 'running', 'in_progress'].includes(s)) return 'pending';
	return 'default';
}

export function statusColor(status: number | null | undefined): string {
	if (!status) return 'text-muted-foreground';
	if (status < 300) return 'text-success';
	if (status < 400) return 'text-accent-yellow';
	return 'text-danger';
}
