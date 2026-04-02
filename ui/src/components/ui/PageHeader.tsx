import React from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
	category?: string;
	title: string;
	description?: string;
	actions?: React.ReactNode;
	className?: string;
}

export function PageHeader({ category, title, description, actions, className }: PageHeaderProps) {
	return (
		<div className={cn('flex items-start justify-between gap-4', className)}>
			<div>
				{category && (
					<p className="text-muted-foreground mb-1 text-xs font-medium tracking-wider uppercase">
						{category}
					</p>
				)}
				<h1 className="text-foreground text-2xl font-bold">{title}</h1>
				{description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
			</div>
			{actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
		</div>
	);
}
