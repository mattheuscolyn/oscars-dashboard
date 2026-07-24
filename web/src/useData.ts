import { useEffect, useState } from 'react'
import type { HistoryData, LatestData } from './types'

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${import.meta.env.BASE_URL}${path}`)
  if (!res.ok) {
    throw new Error(`Failed to load ${path}: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function useDashboardData() {
  const [latest, setLatest] = useState<LatestData | null>(null)
  const [history, setHistory] = useState<HistoryData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [l, h] = await Promise.all([
          fetchJson<LatestData>('data/latest.json'),
          fetchJson<HistoryData>('data/history.json'),
        ])
        if (!cancelled) {
          setLatest(l)
          setHistory(h)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return { latest, history, error, loading }
}
