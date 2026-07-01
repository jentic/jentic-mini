/**
 * audioCue — a tiny WebAudio "ping" used as an opt-in cue when a critical
 * agent-stream event arrives. Deliberately dependency-free and lazy: the
 * AudioContext is created on first use (a user gesture has always happened by
 * then — the toggle that enables it) and reused thereafter.
 *
 * No-ops in non-browser / unsupported environments so callers never need to
 * guard. Failures are swallowed: an audio cue is a nicety, never load-bearing.
 */
let ctx: AudioContext | null = null;

function getContext(): AudioContext | null {
	if (typeof window === 'undefined') return null;
	const Ctor =
		window.AudioContext ??
		(window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
	if (!Ctor) return null;
	if (!ctx) {
		try {
			ctx = new Ctor();
		} catch {
			return null;
		}
	}
	return ctx;
}

/** Play a short two-tone alert. Safe to call from any environment. */
export function playCriticalCue(): void {
	const audio = getContext();
	if (!audio) return;
	try {
		if (audio.state === 'suspended') void audio.resume();
		const now = audio.currentTime;
		const gain = audio.createGain();
		gain.gain.setValueAtTime(0.0001, now);
		gain.gain.exponentialRampToValueAtTime(0.12, now + 0.01);
		gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);
		gain.connect(audio.destination);

		const osc = audio.createOscillator();
		osc.type = 'sine';
		osc.frequency.setValueAtTime(880, now);
		osc.frequency.setValueAtTime(660, now + 0.16);
		osc.connect(gain);
		osc.start(now);
		osc.stop(now + 0.34);
	} catch {
		/* an audio cue is never load-bearing — ignore failures */
	}
}
