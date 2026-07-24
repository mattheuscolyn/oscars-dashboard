import { useMemo, useState } from 'react'
import type { LatestData, SourceKey } from '../types'
import { formatExpected, formatPct, releaseLabel } from '../utils'
import { SourceToggle } from './SourceToggle'

interface Props {
  latest: LatestData
  source: SourceKey
  onSourceChange: (s: SourceKey) => void
}

type MetaFilter = 'all' | 'has' | 'missing'

export function WatchPriority({ latest, source, onSourceChange }: Props) {
  const [metaFilter, setMetaFilter] = useState<MetaFilter>('all')
  const [query, setQuery] = useState('')

  const rows = useMemo(() => {
    let list = latest.watch_priority[source] || []
    if (metaFilter === 'has') list = list.filter((r) => r.has_metadata)
    if (metaFilter === 'missing') list = list.filter((r) => !r.has_metadata)
    const q = query.trim().toLowerCase()
    if (q) list = list.filter((r) => r.film.toLowerCase().includes(q))
    return list
  }, [latest, source, metaFilter, query])

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Watch priority</h2>
          <p className="lede">
            Films ranked by estimated chance of at least one nomination
            (1 − ∏(1 − p<sub>c</sub>) across categories). Independence is an
            approximation — use this to prioritize what to watch, not as a
            forecast.
          </p>
        </div>
        <SourceToggle value={source} onChange={onSourceChange} />
      </header>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Filter films…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter films"
        />
        <div className="pill-group" role="group" aria-label="Metadata filter">
          {(
            [
              ['all', 'All'],
              ['has', 'Has release data'],
              ['missing', 'Missing data'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={metaFilter === id ? 'active' : ''}
              onClick={() => setMetaFilter(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Film</th>
              <th>P(≥1 nom)</th>
              <th>Expected noms</th>
              <th>Top categories</th>
              <th>Release</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.film} className={!row.has_metadata ? 'missing' : ''}>
                <td className="num">{i + 1}</td>
                <td className="film">{row.film}</td>
                <td className="num strong">{formatPct(row.p_at_least_one)}</td>
                <td className="num">{formatExpected(row.expected_noms)}</td>
                <td className="cats">
                  {row.categories.slice(0, 3).map((c) => (
                    <span key={c.category} className="cat-chip">
                      {c.category.replace(/^Best\s+/, '')} {formatPct(c.pct, 0)}
                    </span>
                  ))}
                </td>
                <td className="release">{releaseLabel(row)}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  No films match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
