import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
	hoverable?: boolean;
	children?: React.ReactNode;
	className?: string;
}

export function Card({ hoverable, children, className = '', onClick, ...props }: CardProps) {
	return (
		<div
			className={`bg-muted border-border rounded-xl border transition-all ${
				hoverable ? 'hover:border-primary/50 hover:bg-muted/80 cursor-pointer' : ''
			} ${className}`}
			onClick={onClick}
			{...props}
		>
			{children}
		</div>
	);
}

export function CardHeader({
	children,
	className = '',
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return <div className={`border-border border-b px-5 py-4 ${className}`}>{children}</div>;
}

export function CardBody({
	children,
	className = '',
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}

export function CardTitle({
	children,
	className = '',
}: {
	children: React.ReactNode;
	className?: string;
}) {
	return (
		<h3 className={`font-heading text-foreground font-semibold ${className}`}>{children}</h3>
	);
}
