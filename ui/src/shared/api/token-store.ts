/**
 * Bearer-JWT token store.
 *
 * jentic-one auth is stateless Bearer-JWT (HS256): `POST /auth/login` returns
 * an `access_token` that must be sent as `Authorization: Bearer <token>` on
 * every protected request. There is no logout endpoint — sign-out is purely
 * client-side disposal of the token (see the auth recon contract).
 *
 * The token is held in memory (the source of truth for the request layer) and
 * mirrored to localStorage so a page refresh keeps the session. Subscribers are
 * notified on every change so the auth context can re-render and the generated
 * client can pick up the new value via its TOKEN resolver.
 */
const STORAGE_KEY = 'jentic-one.access_token';

type Listener = (token: string | null) => void;

let current: string | null = readPersisted();
const listeners = new Set<Listener>();

function readPersisted(): string | null {
	try {
		return window.localStorage.getItem(STORAGE_KEY);
	} catch {
		// localStorage can throw in private-mode / sandboxed contexts — fall back
		// to in-memory only rather than crashing the app.
		return null;
	}
}

function persist(token: string | null): void {
	try {
		if (token === null) {
			window.localStorage.removeItem(STORAGE_KEY);
		} else {
			window.localStorage.setItem(STORAGE_KEY, token);
		}
	} catch {
		// Ignore persistence failures; the in-memory token still works for the
		// current page session.
	}
}

export function getToken(): string | null {
	return current;
}

export function setToken(token: string | null): void {
	if (current === token) return;
	current = token;
	persist(token);
	for (const listener of listeners) listener(token);
}

export function clearToken(): void {
	setToken(null);
}

/** Subscribe to token changes. Returns an unsubscribe function. */
export function subscribeToken(listener: Listener): () => void {
	listeners.add(listener);
	return () => {
		listeners.delete(listener);
	};
}
