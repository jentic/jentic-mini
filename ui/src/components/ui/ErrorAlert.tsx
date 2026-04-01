import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ErrorAlertProps {
	message: string;
	className?: string;
}

export function ErrorAlert({ message, className }: ErrorAlertProps) {
	return (
		<div
			role="alert"
			className={cn(
				'bg-danger/10 border-danger/30 text-danger flex items-start gap-3 rounded-lg border px-4 py-3 text-sm',
				className,
			)}
		>
			<AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
			<span>{message}</span>
		</div>
	);
}
