import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
	hoverable?: boolean;
}

export function Card({ hoverable, children, className, onClick, ...props }: CardProps) {
	return (
		<div
			className={cn(
				'bg-muted border-border overflow-hidden rounded-xl border transition-all',
				hoverable && 'hover:border-primary/50 hover:bg-muted/80 cursor-pointer',
				className,
			)}
			onClick={onClick}
			{...props}
		>
			{children}
		</div>
	);
}

export function CardHeader({
	children,
	className,
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return <div className={cn('border-border border-b px-5 py-4', className)}>{children}</div>;
}

export function CardBody({
	children,
	className,
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return <div className={cn('px-5 py-4', className)}>{children}</div>;
}

export function CardFooter({
	children,
	className,
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return <div className={cn('border-border border-t px-5 py-4', className)}>{children}</div>;
}

export function CardTitle({
	children,
	className,
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return (
		<h3 className={cn('font-heading text-foreground font-semibold', className)}>{children}</h3>
	);
}
