/**
 * SheetPrimitive — accessible side/bottom slide-over.
 *
 * Ported from `@jentic/frontend-ui` so the monitor detail sheet can render
 * without pulling in the workspace-internal package. Renders into a portal,
 * traps focus, restores focus on close, and locks background scroll via
 * `overscroll-behavior: contain` (Chrome 144+).
 */

import {
	useEffect,
	useRef,
	useCallback,
	useState,
	type ReactNode,
	type RefObject,
	type JSX,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';

export interface SheetPrimitiveProps {
	open: boolean;
	onClose: () => void;
	children: ReactNode;
	side?: 'right' | 'bottom' | 'left';
	className?: string;
	overlayClassName?: string;
	preventClose?: boolean;
	initialFocus?: RefObject<HTMLElement | null>;
	onAfterClose?: () => void;
	ariaLabel?: string;
	ariaLabelledBy?: string;
}

const FOCUSABLE_SELECTOR = [
	'button:not([disabled])',
	'[href]',
	'input:not([disabled])',
	'select:not([disabled])',
	'textarea:not([disabled])',
	'[tabindex]:not([tabindex="-1"])',
].join(', ');

const ANIMATION_DURATION = 300;

const SIDE_STYLES = {
	right: {
		container: 'inset-y-0 right-0',
		panel: 'h-full w-full sm:w-[480px] sm:max-w-[90vw]',
		enter: 'translate-x-0',
		exit: 'translate-x-full',
	},
	left: {
		container: 'inset-y-0 left-0',
		panel: 'h-full w-full sm:w-[480px] sm:max-w-[90vw]',
		enter: 'translate-x-0',
		exit: '-translate-x-full',
	},
	bottom: {
		container: 'inset-x-0 bottom-0',
		panel: 'w-full max-h-[85dvh] rounded-t-xl overflow-hidden flex flex-col',
		enter: 'translate-y-0',
		exit: 'translate-y-full',
	},
};

export function SheetPrimitive({
	open,
	onClose,
	children,
	side = 'right',
	className,
	overlayClassName,
	preventClose = false,
	initialFocus,
	onAfterClose,
	ariaLabel,
	ariaLabelledBy,
}: SheetPrimitiveProps): JSX.Element | null {
	const sheetRef = useRef<HTMLDivElement>(null);
	const previousFocusRef = useRef<HTMLElement | null>(null);
	const [animationState, setAnimationState] = useState<
		'closed' | 'entering' | 'open' | 'exiting'
	>('closed');
	const [mounted, setMounted] = useState(false);

	const styles = SIDE_STYLES[side];

	useEffect(() => {
		setMounted(true);
	}, []);

	useEffect(() => {
		if (open) {
			if (animationState === 'closed') {
				setAnimationState('entering');
			}
		} else {
			if (animationState === 'open' || animationState === 'entering') {
				setAnimationState('exiting');
			}
		}
	}, [open]);

	useEffect(() => {
		if (animationState === 'entering') {
			const enterTimer = requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					setAnimationState('open');
				});
			});
			return () => cancelAnimationFrame(enterTimer);
		}

		if (animationState === 'exiting') {
			const exitTimer = setTimeout(() => {
				setAnimationState('closed');
				onAfterClose?.();
			}, ANIMATION_DURATION);
			return () => clearTimeout(exitTimer);
		}
	}, [animationState, onAfterClose]);

	useEffect(() => {
		if (animationState === 'entering') {
			previousFocusRef.current = document.activeElement as HTMLElement;
		}

		if (animationState === 'open') {
			const timer = setTimeout(() => {
				if (initialFocus?.current) {
					initialFocus.current.focus();
				} else {
					const firstFocusable =
						sheetRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
					firstFocusable?.focus();
				}
			}, 50);
			return () => clearTimeout(timer);
		}
	}, [animationState, initialFocus]);

	useEffect(() => {
		if (animationState === 'closed' && previousFocusRef.current) {
			const elementToFocus = previousFocusRef.current;
			previousFocusRef.current = null;
			setTimeout(() => {
				elementToFocus?.focus();
			}, 10);
		}
	}, [animationState]);

	useEffect(() => {
		if (animationState !== 'closed') {
			document.documentElement.style.setProperty('overscroll-behavior', 'contain');
			document.body.style.setProperty('overscroll-behavior', 'contain');
		} else {
			document.documentElement.style.removeProperty('overscroll-behavior');
			document.body.style.removeProperty('overscroll-behavior');
		}
	}, [animationState]);

	useEffect(() => {
		return () => {
			document.documentElement.style.removeProperty('overscroll-behavior');
			document.body.style.removeProperty('overscroll-behavior');
		};
	}, []);

	const handleKeyDown = useCallback(
		(e: KeyboardEvent) => {
			if (animationState !== 'open') return;

			if (e.key === 'Escape' && !preventClose) {
				e.preventDefault();
				onClose();
				return;
			}

			if (e.key === 'Tab') {
				const focusable =
					sheetRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
				if (!focusable?.length) return;
				const first = focusable[0];
				const last = focusable[focusable.length - 1];
				if (e.shiftKey && document.activeElement === first) {
					e.preventDefault();
					last.focus();
				} else if (!e.shiftKey && document.activeElement === last) {
					e.preventDefault();
					first.focus();
				}
			}
		},
		[animationState, onClose, preventClose],
	);

	useEffect(() => {
		document.addEventListener('keydown', handleKeyDown);
		return () => document.removeEventListener('keydown', handleKeyDown);
	}, [handleKeyDown]);

	const handleBackdropClick = useCallback(() => {
		if (!preventClose && animationState === 'open') {
			onClose();
		}
	}, [preventClose, onClose, animationState]);

	if (!mounted || animationState === 'closed') return null;

	const isVisible = animationState === 'open';

	return createPortal(
		<div className="fixed inset-0 z-50" style={{ overscrollBehavior: 'contain' }}>
			<div
				className={cn(
					'absolute inset-0 overflow-hidden bg-black/50 backdrop-blur-sm',
					'transition-opacity duration-300 ease-out',
					isVisible ? 'opacity-100' : 'opacity-0',
					overlayClassName,
				)}
				style={{ overscrollBehavior: 'contain' }}
				onClick={handleBackdropClick}
				aria-hidden="true"
			/>

			<div className={cn('fixed', styles.container)}>
				<div
					ref={sheetRef}
					role="dialog"
					aria-modal="true"
					aria-label={ariaLabel}
					aria-labelledby={ariaLabelledBy}
					className={cn(
						'bg-card border-border shadow-xl',
						'transition-transform duration-300 ease-out',
						styles.panel,
						side === 'right' && 'border-l',
						side === 'left' && 'border-r',
						side === 'bottom' && 'border-t',
						isVisible ? styles.enter : styles.exit,
						className,
					)}
					style={{
						willChange: 'transform',
						overscrollBehavior: 'contain',
					}}
				>
					{children}
				</div>
			</div>
		</div>,
		document.body,
	);
}
