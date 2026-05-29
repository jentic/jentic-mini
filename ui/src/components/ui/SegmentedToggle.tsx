import { type JSX } from 'react';
import { LayoutGroup, motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface SegmentedToggleOption<T extends string = string> {
	value: T;
	label: string;
}

interface SegmentedToggleProps<T extends string = string> {
	options: SegmentedToggleOption<T>[];
	value: T;
	onChange: (value: T) => void;
	layoutId: string;
	className?: string;
}

export function SegmentedToggle<T extends string = string>({
	options,
	value,
	onChange,
	layoutId,
	className,
}: SegmentedToggleProps<T>): JSX.Element {
	return (
		<LayoutGroup id={layoutId}>
			<div
				className={cn('border-border bg-muted/50 flex rounded-lg border p-0.5', className)}
			>
				{options.map((option) => {
					const isActive = value === option.value;
					return (
						// eslint-disable-next-line no-restricted-syntax -- SegmentedToggle is a primitive
						<button
							key={option.value}
							type="button"
							onClick={() => onChange(option.value)}
							className={cn(
								'relative rounded-md px-3 py-1 text-xs font-medium transition-colors',
								!isActive && 'cursor-pointer',
							)}
						>
							{isActive && (
								<motion.div
									layoutId={`activeSegment-${layoutId}`}
									className="bg-foreground/10 ring-border/50 absolute inset-0 rounded-md shadow-sm ring-1"
									transition={{
										type: 'spring',
										stiffness: 500,
										damping: 35,
									}}
								/>
							)}
							<span
								className={cn(
									'relative z-10 transition-colors',
									isActive
										? 'text-foreground'
										: 'text-muted-foreground hover:text-foreground',
								)}
							>
								{option.label}
							</span>
						</button>
					);
				})}
			</div>
		</LayoutGroup>
	);
}
