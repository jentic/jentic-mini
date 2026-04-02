import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingStateProps {
	message?: string;
	icon?: React.ReactNode;
	className?: string;
}

export function LoadingState({
	message = 'Loading...',
	icon = <Loader2 className="h-6 w-6 animate-spin" />,
	className,
}: LoadingStateProps) {
	return (
		<div
			className={cn('flex flex-col items-center justify-center py-16 text-center', className)}
		>
			{icon && <div className="text-muted-foreground mb-3">{icon}</div>}
			<p className="text-muted-foreground text-sm">{message}</p>
		</div>
	);
}
