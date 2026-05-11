import { useEffect, useState } from 'react';
import { apiUrl } from '@/api/client';

interface UpdateStatus {
	currentVersion: string | null;
	latestVersion: string | null;
	updateAvailable: boolean;
	releaseUrl: string | null;
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

export function useUpdateCheck(): UpdateStatus {
	const [status, setStatus] = useState<UpdateStatus>({
		currentVersion: null,
		latestVersion: null,
		updateAvailable: false,
		releaseUrl: null,
	});

	useEffect(() => {
		// Only check once per session
		const cached = sessionStorage.getItem('jentic_update_check');
		if (cached) {
			try {
				setStatus(JSON.parse(cached));
				return;
			} catch {
				// ignore bad cache
			}
		}

		async function check() {
			try {
				// Backend proxies the GitHub check with a 6h server-side cache —
				// avoids browser hitting GitHub directly (rate limits, private repos)
				const res = await fetch(apiUrl('/version'));
				if (!res.ok) return;
				const data = await res.json();

				const currentVersion: string = data.current || 'unknown';
				const latestVersion: string = data.latest || '';
				const releaseUrl: string = data.release_url || '';

				const updateAvailable = latestVersion
					? isNewer(latestVersion, currentVersion)
					: false;
				const result: UpdateStatus = {
					currentVersion,
					latestVersion: latestVersion || null,
					updateAvailable,
					releaseUrl: releaseUrl || null,
				};

				try {
					sessionStorage.setItem('jentic_update_check', JSON.stringify(result));
				} catch {
					/* private browsing */
				}
				setStatus(result);
			} catch {
				// Silently ignore — network errors, etc.
			}
		}

		check();
	}, []);

	return status;
}
