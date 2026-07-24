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
import { alwaysTopN, formatPct, risersFallers } from '../utils'
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

export function Momentum({ latest, history, source, onSourceChange }: Props) {
  const topFilms = (latest.watch_priority[source] || []).slice(0, 8).map((r) => r.film)
  const [selected, setSelected] = useState<string[]>(topFilms)
  const [windowDays, setWindowDays] = useState<number | 'all'>(30)

  // Sync selection when source changes and selection empty
  const effectiveSelected = selected.length ? selected : topFilms

  const chartData = useMemo(() => {
    const watch = history.watch[source] || {}
    const dates = history.dates
    return dates.map((date) => {
      const row: Record<string, string | number | null> = { date }
      for (const film of effectiveSelected) {
        const pt = watch[film]?.find((p) => p.date === date)
        row[film] = pt ? pt.p_at_least_one : null
      }
      return row
    })
  }, [history, source, effectiveSelected])

  const { risers, fallers } = useMemo(
    () => risersFallers(history, source, windowDays),
    [history, source, windowDays],
  )

  const sticky = useMemo(
    () => alwaysTopN(history, source, 10),
    [history, source],
  )

  const allFilms = useMemo(() => {
    return (latest.watch_priority[source] || []).map((r) => r.film)
  }, [latest, source])

  function toggleFilm(film: string) {
    setSelected((prev) => {
      const base = prev.length ? prev : topFilms
      return base.includes(film)
        ? base.filter((f) => f !== film)
        : [...base, film].slice(0, 8)
    })
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Momentum</h2>
          <p className="lede">
            How P(≥1 nomination) has shifted over time. Early season swings
            should be large — that is the point.
          </p>
        </div>
        <SourceToggle value={source} onChange={onSourceChange} />
      </header>

      <div className="film-picks">
        {allFilms.slice(0, 20).map((film) => (
          <button
            key={film}
            type="button"
            className={effectiveSelected.includes(film) ? 'active' : ''}
            onClick={() => toggleFilm(film)}
          >
            {film}
          </button>
        ))}
      </div>

      <div className="chart-frame">
        {history.dates.length < 2 ? (
          <p className="empty-chart">
            Need at least two daily scrapes before a trend line appears. Check
            back after the next scheduled run.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(44,58,74,0.12)" strokeDasharray="3 6" />
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
              {effectiveSelected.map((film, i) => (
                <Line
                  key={film}
                  type="monotone"
                  dataKey={film}
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

      <div className="toolbar">
        <div className="pill-group" role="group" aria-label="Window">
          {(
            [
              [7, '7 days'],
              [30, '30 days'],
              ['all', 'All time'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={String(id)}
              type="button"
              className={windowDays === id ? 'active' : ''}
              onClick={() => setWindowDays(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="split-lists">
        <div>
          <h3>Biggest risers</h3>
          <ol className="change-list">
            {risers.map((r) => (
              <li key={r.film}>
                <span>{r.film}</span>
                <span className="up">+{formatPct(r.delta)}</span>
              </li>
            ))}
            {risers.length === 0 && <li className="empty">No risers yet.</li>}
          </ol>
        </div>
        <div>
          <h3>Biggest fallers</h3>
          <ol className="change-list">
            {fallers.map((r) => (
              <li key={r.film}>
                <span>{r.film}</span>
                <span className="down">{formatPct(r.delta)}</span>
              </li>
            ))}
            {fallers.length === 0 && <li className="empty">No fallers yet.</li>}
          </ol>
        </div>
        <div>
          <h3>Always in top 10</h3>
          <ul className="change-list plain">
            {sticky.map((film) => (
              <li key={film}>{film}</li>
            ))}
            {sticky.length === 0 && (
              <li className="empty">
                {history.dates.length < 2
                  ? 'Appears after multiple scrapes.'
                  : 'No film has stayed in the top 10 every day.'}
              </li>
            )}
          </ul>
        </div>
      </div>
    </section>
  )
}
