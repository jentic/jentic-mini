import React from 'react';
import { cn } from '@/lib/utils';

type LabelProps = React.ComponentProps<'label'> & {
	required?: boolean;
};

export function Label({ required, children, className, ...props }: LabelProps) {
	return (
		<label className={cn('text-foreground text-sm font-medium', className)} {...props}>
			{children}
			{required && <span className="text-danger ml-1">*</span>}
		</label>
	);
}
