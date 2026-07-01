import { useRef, useState, useEffect, useCallback, useId, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface TruncateWithTooltipProps {
	children: ReactNode;
	className?: string;
}

/**
 * Renders children in a single truncated line. When the content overflows,
 * hovering (or focusing via keyboard) shows a fixed-position tooltip with the
 * full text that escapes any overflow-hidden ancestors (e.g. the detail
 * sheet's scroll container). The trigger only becomes focusable when it
 * actually overflows, so non-truncated cells stay out of the tab order.
 */
export function TruncateWithTooltip({ children, className = '' }: TruncateWithTooltipProps) {
	const ref = useRef<HTMLSpanElement>(null);
	const [overflows, setOverflows] = useState(false);
	const [show, setShow] = useState(false);
	const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
	const tooltipId = useId();

	useEffect(() => {
		const el = ref.current;
		if (!el) return;
		const check = () => setOverflows(el.scrollWidth > el.clientWidth);
		check();
		const ro = new ResizeObserver(check);
		ro.observe(el);
		return () => ro.disconnect();
	}, [children]);

	const open = useCallback(() => {
		if (!overflows || !ref.current) return;
		const rect = ref.current.getBoundingClientRect();
		setPos({ top: rect.bottom + 4, left: rect.left });
		setShow(true);
	}, [overflows]);

	const close = useCallback(() => {
		setShow(false);
	}, []);

	return (
		<span
			ref={ref}
			className={`block truncate ${className}`}
			tabIndex={overflows ? 0 : undefined}
			aria-describedby={show ? tooltipId : undefined}
			onMouseEnter={open}
			onMouseLeave={close}
			onFocus={open}
			onBlur={close}
		>
			{children}
			{show &&
				pos &&
				createPortal(
					<span
						id={tooltipId}
						role="tooltip"
						className="bg-card text-card-foreground border-border pointer-events-none fixed z-[9999] max-w-[320px] rounded-md border px-2.5 py-1.5 text-xs whitespace-normal shadow-lg"
						style={{ top: pos.top, left: pos.left }}
					>
						{children}
					</span>,
					document.body,
				)}
		</span>
	);
}
