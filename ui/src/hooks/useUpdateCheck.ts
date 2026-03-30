import { useEffect, useState } from 'react';

interface UpdateStatus {
	currentVersion: string | null;
	latestVersion: string | null;
	updateAvailable: boolean;
	releaseUrl: string | null;
	upgradeAvailable: boolean;
}

function parseSemver(v: string): number[] {
	return v
		.replace(/^v/, '')
		.split('.')
		.map((n) => parseInt(n, 10) || 0);
}

function isSemver(v: string): boolean {
	return /^\d+\.\d+\.\d+/.test(v.replace(/^v/, ''));
}

function isNewer(latest: string, current: string): boolean {
	if (!isSemver(latest) || !isSemver(current)) return false;
	const l = parseSemver(latest);
	const c = parseSemver(current);
	for (let i = 0; i < 3; i++) {
		if ((l[i] ?? 0) > (c[i] ?? 0)) return true;
		if ((l[i] ?? 0) < (c[i] ?? 0)) return false;
	}
	return false;
}

const CACHE_KEY = 'jentic_update_check';

export function useUpdateCheck(): UpdateStatus {
	const [status, setStatus] = useState<UpdateStatus>({
		currentVersion: null,
		latestVersion: null,
		updateAvailable: false,
		releaseUrl: null,
		upgradeAvailable: false,
	});

	useEffect(() => {
		async function check() {
			try {
				const res = await fetch('/version');
				if (!res.ok) return;
				const data = await res.json();

				const currentVersion: string = data.current || 'unknown';
				const latestVersion: string = data.latest || '';
				const releaseUrl: string = data.release_url || '';

				if (!latestVersion) return;

				const updateAvailable = isNewer(latestVersion, currentVersion);
				const upgradeAvailable = updateAvailable && !!data.upgrade_available;
				const result: UpdateStatus = {
					currentVersion,
					latestVersion,
					updateAvailable,
					releaseUrl,
					upgradeAvailable,
				};

				try {
					sessionStorage.setItem(CACHE_KEY, JSON.stringify(result));
				} catch {
					/* private browsing */
				}
				setStatus(result);
			} catch {
				// Silently ignore — network errors, etc.
			}
		}

		// Use cache only if the currentVersion still matches the running server.
		// After an upgrade the version changes, so the stale cache is discarded.
		const cached = sessionStorage.getItem(CACHE_KEY);
		if (cached) {
			try {
				const parsed = JSON.parse(cached);
				fetch('/health')
					.then((r) => (r.ok ? r.json() : null))
					.then((health) => {
						if (health?.version && parsed.currentVersion !== health.version) {
							sessionStorage.removeItem(CACHE_KEY);
							check();
						}
					})
					.catch(() => {});
				setStatus(parsed);
				return;
			} catch {
				// ignore bad cache
			}
		}

		check();
	}, []);

	return status;
}
