/**
 * Helpers for surfacing fetch errors to the UI without leaking raw HTML
 * bodies from misbehaving proxies or framework error pages.
 *
 * The convention across the app used to be `throw new Error(await r.text())`,
 * which routes whatever the server returned — JSON, plain text, a 502 HTML
 * page from a reverse proxy — straight into ErrorAlert. That's a bad UX:
 * users see ``<!doctype html><html...>`` rendered as a banner, and the real
 * problem (HTTP status + a short reason) is buried.
 *
 * Instead, prefer:
 *
 * ```ts
 * if (!r.ok) throw await parseApiError(r);
 * ```
 *
 * which yields:
 *
 *   - JSON `{ detail: "..." }` → "..."
 *   - JSON `{ detail: { error_description: "..." } }` (OAuth shape) → "..."
 *   - Anything else → "Request failed (HTTP {status})"
 */

interface ApiError extends Error {
	status: number;
}

export async function parseApiError(response: Response, fallback?: string): Promise<ApiError> {
	let message: string | null = null;
	try {
		const ct = response.headers.get('content-type') ?? '';
		if (ct.includes('application/json')) {
			const body: unknown = await response.json();
			message = extractMessage(body);
		}
	} catch {
		// JSON parse / read failed — fall through to the status-only message.
	}

	const finalMessage = message ?? fallback ?? `Request failed (HTTP ${response.status})`;
	const err = new Error(finalMessage) as ApiError;
	err.status = response.status;
	return err;
}

function extractMessage(body: unknown): string | null {
	if (!body || typeof body !== 'object') return null;
	const obj = body as Record<string, unknown>;

	const detail = obj.detail;
	if (typeof detail === 'string') return detail;
	if (detail && typeof detail === 'object') {
		const inner = detail as Record<string, unknown>;
		if (typeof inner.error_description === 'string') return inner.error_description;
		if (typeof inner.error === 'string') return inner.error;
	}

	if (typeof obj.error_description === 'string') return obj.error_description;
	if (typeof obj.error === 'string') return obj.error;
	if (typeof obj.message === 'string') return obj.message;

	return null;
}
