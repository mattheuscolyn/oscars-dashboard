import { useMemo, useState } from 'react'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from 'recharts'
import type { HistoryData, LatestData, SourceKey } from '../types'
import { formatPct } from '../utils'
import { SourceToggle } from './SourceToggle'

interface Props {
  latest: LatestData
  history: HistoryData
  source: SourceKey
  onSourceChange: (s: SourceKey) => void
}

export function ByCategory({ latest, history, source, onSourceChange }: Props) {
  const categories = useMemo(() => {
    return Object.keys(latest.categories[source] || {}).sort()
  }, [latest, source])

  const [category, setCategory] = useState(categories[0] || '')

  const activeCategory =
    category && categories.includes(category)
      ? category
      : categories[0] || ''

  const standings = latest.categories[source]?.[activeCategory] || []

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>By category</h2>
          <p className="lede">
            Current nomination odds for a single race, with sparklines as
            history accumulates. New categories appear automatically when Gold
            Derby adds them.
          </p>
        </div>
        <SourceToggle value={source} onChange={onSourceChange} />
      </header>

      <div className="toolbar">
        <label className="select-label">
          Category
          <select
            value={activeCategory}
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Contender</th>
              <th>Film</th>
              <th>Odds</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((row) => {
              const series =
                history.category[source]?.[activeCategory]?.[row.film] || []
              const spark = series.map((p) => ({
                date: p.date,
                pct: p.pct,
              }))
              return (
                <tr key={`${row.rank}-${row.candidate}-${row.film}`}>
                  <td className="num">{row.rank}</td>
                  <td>{row.candidate}</td>
                  <td className="film">{row.film}</td>
                  <td className="num strong">{formatPct(row.pct)}</td>
                  <td className="spark">
                    {spark.length >= 2 ? (
                      <ResponsiveContainer width={120} height={36}>
                        <LineChart data={spark}>
                          <YAxis domain={[0, 100]} hide />
                          <Tooltip
                            formatter={(v) =>
                              typeof v === 'number' ? formatPct(v) : '—'
                            }
                          />
                          <Line
                            type="monotone"
                            dataKey="pct"
                            stroke="#8b6914"
                            strokeWidth={1.5}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
            {standings.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  No standings for this category yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
