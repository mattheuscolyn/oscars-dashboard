import type { HistoryData, HistoryPoint, SourceKey, WatchRow } from './types'

export function formatPct(n: number, digits = 1): string {
  return `${n.toFixed(digits)}%`
}

export function formatExpected(n: number): string {
  return n.toFixed(2)
}

/** ISO YYYY-MM-DD → "Nov 6, 2026" (UTC, no timezone shift). */
export function formatReleaseDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim())
  if (!m) return iso
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ]
  const year = m[1]
  const month = months[Number(m[2]) - 1]
  const day = String(Number(m[3]))
  if (!month) return iso
  return `${month} ${day}, ${year}`
}

function theatricalPhrase(type: string): string {
  const t = type.trim().toLowerCase()
  if (t === 'wide') return 'Wide release'
  if (t === 'limited') return 'Limited release'
  if (t === 'tba') return 'Theatrical TBA'
  if (t) return `${type} release`
  return 'In theaters'
}

/** Compact one-line summary for tables / cards. */
export function releaseLabel(
  row: Pick<
    WatchRow,
    | 'premiere_date'
    | 'theatrical_date'
    | 'theatrical_type'
    | 'streaming_date'
    | 'streaming_platform'
    | 'certification'
    | 'has_metadata'
  >,
): string {
  if (!row.has_metadata) return 'Missing metadata'
  const parts: string[] = []

  if (row.theatrical_date) {
    parts.push(
      `${formatReleaseDate(row.theatrical_date)} · ${theatricalPhrase(row.theatrical_type)}`,
    )
  } else if (row.premiere_date) {
    parts.push(`${formatReleaseDate(row.premiere_date)} · Premiere`)
  }

  if (row.streaming_date) {
    const when = formatReleaseDate(row.streaming_date)
    const plat = row.streaming_platform?.trim()
    parts.push(plat ? `${when} · ${plat}` : `${when} · Digital`)
  }

  if (row.certification?.trim()) {
    parts.push(`Rated ${row.certification.trim()}`)
  }

  if (!parts.length) return 'Dates TBA'
  return parts.join(' · ')
}

/** Structured lines for the release calendar. */
export function releaseDetailLines(
  row: Pick<
    WatchRow,
    | 'premiere_date'
    | 'theatrical_date'
    | 'theatrical_type'
    | 'streaming_date'
    | 'streaming_platform'
    | 'certification'
  >,
): string[] {
  const lines: string[] = []
  if (row.premiere_date) {
    lines.push(`Premiere · ${formatReleaseDate(row.premiere_date)}`)
  }
  if (row.theatrical_date) {
    lines.push(
      `${theatricalPhrase(row.theatrical_type)} · ${formatReleaseDate(row.theatrical_date)}`,
    )
  }
  if (row.streaming_date) {
    const plat = row.streaming_platform?.trim()
    lines.push(
      plat
        ? `${plat} · ${formatReleaseDate(row.streaming_date)}`
        : `Digital · ${formatReleaseDate(row.streaming_date)}`,
    )
  }
  if (row.certification?.trim()) {
    lines.push(`Rated ${row.certification.trim()}`)
  }
  return lines
}

export function deltaOverWindow(
  series: HistoryPoint[] | undefined,
  windowDays: number | 'all',
): number | null {
  if (!series || series.length < 2) return null
  const last = series[series.length - 1]
  if (windowDays === 'all') {
    return last.p_at_least_one - series[0].p_at_least_one
  }
  const cutoff = addDays(last.date, -windowDays)
  // Prefer point nearest to cutoff from at-or-before
  const before = [...series].reverse().find((p) => p.date <= cutoff)
  const base = before ?? series[0]
  return last.p_at_least_one - base.p_at_least_one
}

function addDays(isoDate: string, days: number): string {
  const d = new Date(isoDate + 'T00:00:00Z')
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function risersFallers(
  history: HistoryData,
  source: SourceKey,
  windowDays: number | 'all',
  limit = 8,
): { risers: { film: string; delta: number }[]; fallers: { film: string; delta: number }[] } {
  const watch = history.watch[source] || {}
  const scored: { film: string; delta: number }[] = []
  for (const [film, series] of Object.entries(watch)) {
    const delta = deltaOverWindow(series, windowDays)
    if (delta === null) continue
    scored.push({ film, delta })
  }
  const sorted = [...scored].sort((a, b) => b.delta - a.delta)
  return {
    risers: sorted.filter((s) => s.delta > 0).slice(0, limit),
    fallers: [...sorted].filter((s) => s.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, limit),
  }
}

export function alwaysTopN(
  history: HistoryData,
  source: SourceKey,
  n = 10,
): string[] {
  const dates = history.dates
  if (dates.length === 0) return []
  const watch = history.watch[source] || {}
  const films = Object.keys(watch)
  return films.filter((film) => {
    return dates.every((date) => {
      // Rank films by p_at_least_one on this date
      const dayScores = films
        .map((f) => {
          const pt = watch[f]?.find((p) => p.date === date)
          return { film: f, p: pt?.p_at_least_one ?? -1 }
        })
        .filter((x) => x.p >= 0)
        .sort((a, b) => b.p - a.p)
      const idx = dayScores.findIndex((x) => x.film === film)
      return idx >= 0 && idx < n
    })
  })
}

export function csvStub(films: string[]): string {
  const header =
    'film,tmdb_id,poster_path,certification,premiere_date,theatrical_date,theatrical_type,streaming_date,streaming_platform,notes,source'
  const rows = films.map((f) => `"${f.replace(/"/g, '""')}",,,,,,,,,,manual`)
  return [header, ...rows].join('\n')
}

/** Build film → poster_url map from latest payload. */
export function posterIndex(latest: {
  films: { film: string; poster_url?: string }[]
  watch_priority?: Record<string, { film: string; poster_url?: string }[]>
}): Record<string, string> {
  const m: Record<string, string> = {}
  for (const f of latest.films || []) {
    if (f.poster_url) m[f.film] = f.poster_url
  }
  for (const rows of Object.values(latest.watch_priority || {})) {
    for (const r of rows) {
      if (r.poster_url && !m[r.film]) m[r.film] = r.poster_url
    }
  }
  return m
}
