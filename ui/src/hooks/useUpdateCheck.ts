import { useEffect, useState } from 'react'

interface UpdateStatus {
  currentVersion: string | null
  latestVersion: string | null
  updateAvailable: boolean
  releaseUrl: string | null
}

function parseSemver(v: string): number[] {
  return v.replace(/^v/, '').split('.').map(n => parseInt(n, 10) || 0)
}

function isNewer(latest: string, current: string): boolean {
  const l = parseSemver(latest)
  const c = parseSemver(current)
  for (let i = 0; i < 3; i++) {
    if ((l[i] ?? 0) > (c[i] ?? 0)) return true
    if ((l[i] ?? 0) < (c[i] ?? 0)) return false
  }
  return false
}

export function useUpdateCheck(): UpdateStatus {
  const [status, setStatus] = useState<UpdateStatus>({
    currentVersion: null,
    latestVersion: null,
    updateAvailable: false,
    releaseUrl: null,
  })

  useEffect(() => {
    // Only check once per session
    const cached = sessionStorage.getItem('jentic_update_check')
    if (cached) {
      try {
        setStatus(JSON.parse(cached))
        return
      } catch {
        // ignore bad cache
      }
    }

    async function check() {
      try {
        // Get current version from our own /health endpoint
        const healthRes = await fetch('/health')
        if (!healthRes.ok) return
        const health = await healthRes.json()
        const currentVersion: string = health.version || 'dev'

        // Don't bother checking if running a dev build
        if (currentVersion === 'dev') return

        // Check GitHub releases API for latest release
        const ghRes = await fetch(
          'https://api.github.com/repos/jentic/jentic-mini/releases/latest',
          { headers: { Accept: 'application/vnd.github+json' } }
        )
        // 404 = no releases yet — that's fine, stay silent
        if (!ghRes.ok) return

        const release = await ghRes.json()
        const latestVersion: string = release.tag_name || ''
        const releaseUrl: string = release.html_url || ''

        if (!latestVersion) return

        const updateAvailable = isNewer(latestVersion, currentVersion)
        const result: UpdateStatus = {
          currentVersion,
          latestVersion,
          updateAvailable,
          releaseUrl,
        }

        sessionStorage.setItem('jentic_update_check', JSON.stringify(result))
        setStatus(result)
      } catch {
        // Silently ignore — network errors, CORS issues, rate limits, etc.
      }
    }

    check()
  }, [])

  return status
}
