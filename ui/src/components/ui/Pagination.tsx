import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';
import { cn } from '@/lib/utils';

interface PaginationProps {
	page: number;
	totalPages: number;
	onPageChange: (page: number) => void;
	className?: string;
}

export function Pagination({ page, totalPages, onPageChange, className }: PaginationProps) {
	if (totalPages <= 0) return null;

	return (
		<div className={cn('flex items-center justify-between', className)}>
			<Button
				variant="secondary"
				size="sm"
				disabled={page <= 1}
				onClick={() => onPageChange(page - 1)}
			>
				<ChevronLeft className="h-4 w-4" /> Previous
			</Button>
			<span className="text-muted-foreground text-sm">
				Page {page} of {totalPages}
			</span>
			<Button
				variant="secondary"
				size="sm"
				disabled={page >= totalPages}
				onClick={() => onPageChange(page + 1)}
			>
				Next <ChevronRight className="h-4 w-4" />
			</Button>
		</div>
	);
}
