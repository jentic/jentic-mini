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
        // TODO: replace hardcoded version with /version endpoint once backend
        // versioning is properly wired up
        const CURRENT_VERSION = '0.1.0'

        // Backend proxies the GitHub check with a 6h server-side cache —
        // avoids browser hitting GitHub directly (rate limits, private repos)
        const res = await fetch('/version')
        if (!res.ok) return
        const data = await res.json()

        const latestVersion: string = data.latest || ''
        const releaseUrl: string = data.release_url || ''

        if (!latestVersion) return

        const updateAvailable = isNewer(latestVersion, CURRENT_VERSION)
        const result: UpdateStatus = {
          currentVersion: CURRENT_VERSION,
          latestVersion,
          updateAvailable,
          releaseUrl,
        }

        sessionStorage.setItem('jentic_update_check', JSON.stringify(result))
        setStatus(result)
      } catch {
        // Silently ignore — network errors, etc.
      }
    }

    check()
  }, [])

  return status
}
