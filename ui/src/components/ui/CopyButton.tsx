import { Copy, Check } from 'lucide-react';
import { Button } from './Button';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';
import { cn } from '@/lib/utils';

interface CopyButtonProps {
	value: string;
	label?: string;
	className?: string;
}

export function CopyButton({ value, label, className }: CopyButtonProps) {
	const { copied, copy } = useCopyToClipboard();

	return (
		<Button
			variant="secondary"
			size="sm"
			onClick={() => copy(value)}
			className={cn('shrink-0', className)}
		>
			{copied ? (
				<>
					<Check className="text-success h-4 w-4" />
					{label ? 'Copied!' : null}
				</>
			) : (
				<>
					<Copy className="h-4 w-4" />
					{label ?? null}
				</>
			)}
		</Button>
	);
}
