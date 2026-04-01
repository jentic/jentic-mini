import React, { useRef, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

type DialogSize = 'sm' | 'md' | 'lg';

const sizeClasses: Record<DialogSize, string> = {
	sm: 'max-w-sm',
	md: 'max-w-lg',
	lg: 'max-w-2xl',
};

interface DialogProps {
	open: boolean;
	onClose: () => void;
	title: string;
	children: React.ReactNode;
	footer?: React.ReactNode;
	size?: DialogSize;
	className?: string;
}

export function Dialog({
	open,
	onClose,
	title,
	children,
	footer,
	size = 'md',
	className,
}: DialogProps) {
	const dialogRef = useRef<HTMLDialogElement>(null);
	const titleId = `dialog-title-${React.useId()}`;

	useEffect(() => {
		const dialog = dialogRef.current;
		if (!dialog) return;

		if (open && !dialog.open) {
			dialog.showModal();
		} else if (!open && dialog.open) {
			dialog.close();
		}
	}, [open]);

	const handleCancel = useCallback(
		(e: React.SyntheticEvent<HTMLDialogElement>) => {
			e.preventDefault();
			onClose();
		},
		[onClose],
	);

	const handleBackdropClick = useCallback(
		(e: React.MouseEvent<HTMLDialogElement>) => {
			if (e.target === dialogRef.current) {
				onClose();
			}
		},
		[onClose],
	);

	return (
		<dialog
			ref={dialogRef}
			aria-labelledby={titleId}
			onCancel={handleCancel}
			onClick={handleBackdropClick}
			className={cn(
				'bg-muted border-border w-full rounded-xl border p-0 shadow-xl backdrop:bg-black/60',
				sizeClasses[size],
				className,
			)}
		>
			<div className="flex flex-col">
				<div className="border-border flex items-center justify-between border-b px-5 py-4">
					<h2 id={titleId} className="text-foreground text-lg font-semibold">
						{title}
					</h2>
					<button
						type="button"
						onClick={onClose}
						className="text-muted-foreground hover:text-foreground rounded-lg p-1 transition-colors"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>
				<div className="px-5 py-4">{children}</div>
				{footer && (
					<div className="border-border flex items-center justify-end gap-2 border-t px-5 py-4">
						{footer}
					</div>
				)}
			</div>
		</dialog>
	);
}
