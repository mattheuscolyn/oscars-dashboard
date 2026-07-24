import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HistoryData, LatestData, SourceKey } from '../types'
import { formatPct, posterIndex } from '../utils'
import { PosterThumb } from './PosterThumb'
import { SourceToggle } from './SourceToggle'

const PALETTE = [
  '#8b6914',
  '#2c3a4a',
  '#a63d2f',
  '#3d6b5a',
  '#6b4c7a',
  '#b07d3a',
  '#1e4d6b',
  '#7a3e3e',
]

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
  const [selected, setSelected] = useState<string[]>([])

  const activeCategory =
    category && categories.includes(category)
      ? category
      : categories[0] || ''

  const standings = latest.categories[source]?.[activeCategory] || []

  const posters = useMemo(() => posterIndex(latest), [latest])

  const topKeys = useMemo(() => {
    return standings.slice(0, 8).map((r) => seriesKey(r.candidate, r.film))
  }, [standings])

  const effectiveSelected = selected.length ? selected : topKeys

  const chartData = useMemo(() => {
    const catHistory = history.category[source]?.[activeCategory] || {}
    const dates = history.dates
    const seriesByKey: Record<string, { date: string; pct: number }[]> = {}
    for (const row of standings) {
      const key = seriesKey(row.candidate, row.film)
      const historyId =
        row.candidate === row.film
          ? row.film
          : `${row.candidate} || ${row.film}`
      const points =
        catHistory[historyId] ||
        (catHistory[row.film] || []).filter(
          (p) => !p.candidate || p.candidate === row.candidate,
        )
      seriesByKey[key] = points.map((p) => ({
        date: p.date,
        pct: p.pct,
      }))
    }

    return dates.map((date) => {
      const row: Record<string, string | number | null> = { date }
      for (const key of effectiveSelected) {
        const pt = seriesByKey[key]?.find((p) => p.date === date)
        row[key] = pt ? pt.pct : null
      }
      return row
    })
  }, [history, source, activeCategory, standings, effectiveSelected])

  function toggleKey(key: string) {
    setSelected((prev) => {
      const base = prev.length ? prev : topKeys
      return base.includes(key)
        ? base.filter((k) => k !== key)
        : [...base, key].slice(0, 8)
    })
  }

  function onCategoryChange(next: string) {
    setCategory(next)
    setSelected([])
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>By category</h2>
          <p className="lede">
            Nomination odds for a single race over time, plus today’s
            standings. New categories appear automatically when Gold Derby adds
            them.
          </p>
        </div>
        <SourceToggle value={source} onChange={onSourceChange} />
      </header>

      <div className="toolbar">
        <label className="select-label">
          Category
          <select
            value={activeCategory}
            onChange={(e) => onCategoryChange(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="film-picks">
        {standings.slice(0, 16).map((row) => {
          const key = seriesKey(row.candidate, row.film)
          const label =
            row.candidate === row.film
              ? row.film
              : `${row.candidate} (${row.film})`
          return (
            <button
              key={key}
              type="button"
              className={effectiveSelected.includes(key) ? 'active' : ''}
              onClick={() => toggleKey(key)}
            >
              {label}
            </button>
          )
        })}
      </div>

      <div className="chart-frame">
        {history.dates.length < 2 ? (
          <p className="empty-chart">
            Need at least two daily scrapes before a category trend line
            appears.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                stroke="rgba(44,58,74,0.12)"
                strokeDasharray="3 6"
              />
              <XAxis
                dataKey="date"
                tick={{ fill: '#2c3a4a', fontSize: 11 }}
                tickMargin={8}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: '#2c3a4a', fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
                width={42}
              />
              <Tooltip
                formatter={(value) =>
                  typeof value === 'number' ? formatPct(value) : '—'
                }
                contentStyle={{
                  background: '#f7f1e6',
                  border: '1px solid #c4b59a',
                  borderRadius: 0,
                }}
              />
              <Legend />
              {effectiveSelected.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={PALETTE[i % PALETTE.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
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
              const spark = series
                .filter(
                  (p) =>
                    !p.candidate ||
                    p.candidate === row.candidate ||
                    p.candidate === row.film,
                )
                .map((p) => ({
                  date: p.date,
                  pct: p.pct,
                }))
              return (
                <tr key={`${row.rank}-${row.candidate}-${row.film}`}>
                  <td className="num">{row.rank}</td>
                  <td>
                    <span className="film-cell">
                      <PosterThumb
                        url={posters[row.film]}
                        alt={row.film}
                      />
                      <span>{row.candidate}</span>
                    </span>
                  </td>
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

function seriesKey(candidate: string, film: string): string {
  return candidate === film ? film : `${candidate} · ${film}`
}
