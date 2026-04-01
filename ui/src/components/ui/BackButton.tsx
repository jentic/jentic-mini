import { ChevronLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface BackButtonProps {
	to: string;
	label: string;
	className?: string;
}

export function BackButton({ to, label, className }: BackButtonProps) {
	return (
		<Link
			to={to}
			className={cn(
				'text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm transition-colors',
				className,
			)}
		>
			<ChevronLeft className="h-4 w-4" />
			{label}
		</Link>
	);
}
