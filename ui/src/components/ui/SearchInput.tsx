import React, { useId, useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchInputProps {
	value: string;
	onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
	placeholder?: string;
	className?: string;
	inputClassName?: string;
	onClear?: () => void;
	id?: string;
	icon?: LucideIcon;
	/** Compact variant for sidebars and tight spaces. @default 'default' */
	size?: 'default' | 'sm';
	/**
	 * Debounce delay in milliseconds for onChange callback. When set, onChange
	 * fires only after the user stops typing for this duration. The input
	 * still updates immediately for responsive UX.
	 */
	debounceMs?: number;
}

export function SearchInput({
	value,
	onChange,
	onClear,
	id,
	placeholder = 'Search',
	className,
	inputClassName,
	icon: Icon = Search,
	size = 'default',
	debounceMs,
}: SearchInputProps) {
	const generatedId = useId();
	const inputId = id ?? generatedId;
	const isSmall = size === 'sm';

	const [internalValue, setInternalValue] = useState(value);
	const isDebouncing = debounceMs !== undefined && debounceMs > 0;

	const prevValueRef = useRef(value);
	useEffect(() => {
		if (value !== prevValueRef.current) {
			setInternalValue(value);
			prevValueRef.current = value;
		}
	}, [value]);

	useEffect(() => {
		if (!isDebouncing) return;
		const timeoutId = setTimeout(() => {
			if (internalValue !== value) {
				const event = {
					target: { value: internalValue },
				} as React.ChangeEvent<HTMLInputElement>;
				onChange(event);
			}
		}, debounceMs);
		return () => clearTimeout(timeoutId);
	}, [internalValue, debounceMs, isDebouncing, onChange, value]);

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			const newValue = e.target.value;
			if (isDebouncing) {
				setInternalValue(newValue);
			} else {
				onChange(e);
			}
		},
		[isDebouncing, onChange],
	);

	const displayValue = isDebouncing ? internalValue : value;
	const showClear = Boolean(displayValue);

	const handleClear = (e: React.MouseEvent<HTMLButtonElement>) => {
		e.preventDefault();
		if (isDebouncing) setInternalValue('');
		if (onClear) {
			onClear();
		} else {
			const event = {
				target: { value: '' },
			} as React.ChangeEvent<HTMLInputElement>;
			onChange(event);
		}
	};

	return (
		<div className={cn('relative', className)}>
			<Icon
				className={cn(
					'text-muted-foreground pointer-events-none absolute top-1/2 -translate-y-1/2',
					isSmall ? 'left-2.5 h-3.5 w-3.5' : 'left-3 h-5 w-5',
				)}
				aria-hidden="true"
			/>
			{/* eslint-disable-next-line no-restricted-syntax -- SearchInput is a primitive */}
			<input
				id={inputId}
				type="text"
				value={displayValue}
				onChange={handleChange}
				placeholder={placeholder}
				className={cn(
					'border-border bg-card text-foreground placeholder:text-muted-foreground focus:border-primary w-full rounded-lg border transition-colors focus-visible:outline-none',
					isSmall ? 'py-1.5 pr-8 pl-8 text-xs' : 'h-9 py-1 pr-10 pl-10',
					inputClassName,
				)}
				aria-label={placeholder}
			/>
			{showClear && (
				// eslint-disable-next-line no-restricted-syntax -- SearchInput clear is a primitive
				<button
					type="button"
					className={cn(
						'text-muted-foreground hover:text-foreground absolute top-1/2 -translate-y-1/2 cursor-pointer rounded-full transition-colors focus:outline-none',
						isSmall ? 'right-1.5 p-0.5' : 'right-2 p-1',
					)}
					onClick={handleClear}
					aria-label="Clear search"
				>
					<X className={cn(isSmall ? 'h-3.5 w-3.5' : 'h-4 w-4')} aria-hidden="true" />
				</button>
			)}
		</div>
	);
}
