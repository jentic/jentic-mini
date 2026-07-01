/**
 * Returns true if the event target is a text input element where
 * keyboard shortcuts should not fire (input, textarea, select, or
 * contentEditable). Use this guard in global `keydown` handlers to
 * avoid hijacking keystrokes meant for form fields.
 */
export function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	const tag = target.tagName;
	if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
	return target.isContentEditable;
}

/**
 * Platform-aware: true on macOS / iOS, where `⌘` is the modifier key
 * (`Ctrl` elsewhere). Computed once at module load.
 */
export const isMac = (() => {
	if (typeof navigator === 'undefined') return false;
	const nav = navigator as Navigator & { userAgentData?: { platform: string } };
	if (nav.userAgentData?.platform) {
		return nav.userAgentData.platform === 'macOS';
	}
	return /Mac|iPhone|iPad|iPod/.test(navigator.userAgent ?? '');
})();

/** Platform-aware modifier key label: `⌘` on Mac, `Ctrl` elsewhere. */
export const MOD_KEY = isMac ? '⌘' : 'Ctrl';
