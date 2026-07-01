/**
 * Runtime app config the backend that serves the SPA exposes at
 * `/app-config.json` (see src/jentic_one/shared/web/static.py). The admin
 * health endpoint lives at a different path per deploy mode (`/health`
 * standalone vs `/admin/health` combined), so the server tells the SPA which
 * to call rather than the SPA hard-coding one that only works in a single mode.
 *
 * `loadAppConfig()` fetches that endpoint once on boot and stashes the result
 * on `window.__APP_CONFIG__`; `getAppConfig()` then reads it synchronously.
 * When the fetch fails or the global is absent (e.g. the Vite dev server, where
 * `make start-app` is the default backend), the combined-mode defaults apply.
 */
export interface AppConfig {
	healthPath: string;
}

declare global {
	interface Window {
		__APP_CONFIG__?: Partial<AppConfig>;
	}
}

const DEFAULTS: AppConfig = {
	healthPath: '/admin/health',
};

/**
 * Fixed, mode-independent path the backend serves the runtime config from.
 * Kept in sync with `APP_CONFIG_PATH` in `shared/web/static.py`.
 */
const APP_CONFIG_URL = '/app-config.json';

export function getAppConfig(): AppConfig {
	return { ...DEFAULTS, ...(window.__APP_CONFIG__ ?? {}) };
}

/**
 * Fetch the backend's runtime config and cache it on `window.__APP_CONFIG__`.
 * Best-effort: a failed or missing endpoint leaves the defaults in place so the
 * SPA still boots (and works in single-mode dev). Called once before mount.
 */
export async function loadAppConfig(): Promise<void> {
	try {
		const response = await fetch(APP_CONFIG_URL, {
			headers: { Accept: 'application/json' },
		});
		if (!response.ok) return;
		const config = (await response.json()) as Partial<AppConfig>;
		window.__APP_CONFIG__ = { ...window.__APP_CONFIG__, ...config };
	} catch {
		// Leave defaults in place; getAppConfig() falls back to combined mode.
	}
}
