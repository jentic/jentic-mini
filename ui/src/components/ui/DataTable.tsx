import React from 'react';
import { LoadingState } from './LoadingState';
import { cn } from '@/lib/utils';

export type Column<T> = {
	key: keyof T | string;
	header: string;
	render?: (row: T) => React.ReactNode;
	className?: string;
};

interface DataTableProps<T> {
	columns: Column<T>[];
	data: T[];
	getRowKey: (row: T) => string;
	emptyMessage?: string;
	isLoading?: boolean;
	className?: string;
	onRowClick?: (row: T) => void;
}

export function DataTable<T>({
	columns,
	data,
	getRowKey,
	emptyMessage = 'No data found.',
	isLoading,
	className,
	onRowClick,
}: DataTableProps<T>) {
	if (isLoading) {
		return <LoadingState />;
	}

	if (data.length === 0) {
		return <p className="text-muted-foreground py-8 text-center text-sm">{emptyMessage}</p>;
	}

	return (
		<div className={cn('overflow-x-auto', className)}>
			<table className="w-full">
				<thead>
					<tr className="border-border border-b text-left">
						{columns.map((col) => (
							<th
								key={String(col.key)}
								className={cn(
									'text-muted-foreground px-4 py-3 text-xs font-medium tracking-wider uppercase',
									col.className,
								)}
							>
								{col.header}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{data.map((row) => (
						<tr
							key={getRowKey(row)}
							onClick={onRowClick ? () => onRowClick(row) : undefined}
							className={cn(
								'border-border border-b transition-colors last:border-0',
								onRowClick && 'hover:bg-muted/60 cursor-pointer',
							)}
						>
							{columns.map((col) => (
								<td
									key={String(col.key)}
									className={cn('px-4 py-3 text-sm', col.className)}
								>
									{col.render
										? col.render(row)
										: String(
												(row as Record<string, unknown>)[String(col.key)] ??
													'',
											)}
								</td>
							))}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
