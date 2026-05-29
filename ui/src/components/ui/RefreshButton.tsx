import { type JSX, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from './Button';
import { cn } from '@/lib/utils';

interface RefreshButtonProps {
	onRefresh: () => void;
	className?: string;
	iconSize?: string;
	title?: string;
	disabled?: boolean;
}

export function RefreshButton({
	onRefresh,
	className,
	iconSize = 'h-4 w-4',
	title = 'Refresh',
	disabled = false,
}: RefreshButtonProps): JSX.Element {
	const [spinning, setSpinning] = useState(false);

	const handleRefresh = useCallback(() => {
		if (spinning || disabled) return;
		setSpinning(true);
		onRefresh();
		setTimeout(() => setSpinning(false), 600);
	}, [spinning, disabled, onRefresh]);

	return (
		<Button
			type="button"
			variant="ghost"
			size="icon"
			onClick={handleRefresh}
			className={cn('hover:bg-muted/50 shrink-0 cursor-pointer', className)}
			disabled={spinning || disabled}
			title={title}
		>
			<motion.div
				animate={spinning ? { rotate: 360 } : { rotate: 0 }}
				transition={spinning ? { duration: 0.6, ease: 'easeInOut' } : { duration: 0 }}
			>
				<RefreshCw
					className={cn(iconSize, 'text-muted-foreground hover:text-foreground')}
				/>
			</motion.div>
		</Button>
	);
}
