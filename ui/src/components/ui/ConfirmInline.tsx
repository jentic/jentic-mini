import React, { useState } from 'react';
import { Button } from './Button';

type Variant = 'danger' | 'default';

interface ConfirmInlineProps {
	onConfirm: () => void;
	message: string;
	confirmLabel?: string;
	variant?: Variant;
	children: React.ReactElement;
}

export function ConfirmInline({
	onConfirm,
	message,
	confirmLabel = 'Confirm',
	variant = 'danger',
	children,
}: ConfirmInlineProps) {
	const [pending, setPending] = useState(false);

	if (!pending) {
		return React.cloneElement(children, {
			onClick: (e: React.MouseEvent) => {
				e.stopPropagation();
				setPending(true);
			},
		});
	}

	return (
		<div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
			<span className="text-muted-foreground text-xs">{message}</span>
			<Button
				size="sm"
				variant={variant === 'danger' ? 'danger' : 'primary'}
				onClick={() => {
					onConfirm();
					setPending(false);
				}}
			>
				{confirmLabel}
			</Button>
			<Button size="sm" variant="ghost" onClick={() => setPending(false)}>
				Cancel
			</Button>
		</div>
	);
}
