import { useMemo, useState } from 'react'
import type { LatestData, SourceKey } from '../types'
import { csvStub, formatExpected, formatPct } from '../utils'
import { PosterThumb } from './PosterThumb'

interface Props {
  latest: LatestData
  source: SourceKey
}

type CalendarFilter = 'priority' | 'all'

/** Next actionable US date for sorting (theatrical preferred, else digital, else premiere). */
function nextDate(f: {
  theatrical_date: string
  streaming_date: string
  premiere_date: string
}): string {
  return f.theatrical_date || f.streaming_date || f.premiere_date || '9999-99-99'
}

function isUpcoming(iso: string, today: string): boolean {
  return iso >= today
}

export function Releases({ latest, source }: Props) {
  const [copied, setCopied] = useState(false)
  const [filter, setFilter] = useState<CalendarFilter>('priority')
  const [showMissing, setShowMissing] = useState(false)

  const today = useMemo(() => new Date().toISOString().slice(0, 10), [])

  const oddsByFilm = useMemo(() => {
    const map = new Map<
      string,
      { p: number; expected: number; rank: number }
    >()
    ;(latest.watch_priority[source] || []).forEach((row, i) => {
      map.set(row.film, {
        p: row.p_at_least_one,
        expected: row.expected_noms,
        rank: i + 1,
      })
    })
    return map
  }, [latest, source])

  const dated = useMemo(() => {
    const rows = latest.films
      .filter((f) => f.theatrical_date || f.streaming_date || f.premiere_date)
      .map((f) => {
        const odds = oddsByFilm.get(f.film)
        return {
          ...f,
          p: odds?.p ?? 0,
          expected: odds?.expected ?? 0,
          watchRank: odds?.rank ?? 9999,
          when: nextDate(f),
        }
      })

    const rankedByP = [...rows].sort((a, b) => b.p - a.p || b.expected - a.expected)
    const topN = new Set(rankedByP.slice(0, 25).map((r) => r.film))

    const isPriority = (r: (typeof rows)[0]) =>
      r.p >= 20 || r.expected >= 0.5 || topN.has(r.film)

    let list = filter === 'priority' ? rows.filter(isPriority) : rows

    // Priority view: chronological among contenders (plan what to see next).
    // All view: odds-weighted so near-locks float above longshots.
    list = [...list].sort((a, b) => {
      const aUp = isUpcoming(a.when, today) ? 0 : 1
      const bUp = isUpcoming(b.when, today) ? 0 : 1
      if (aUp !== bUp) return aUp - bUp

      if (filter === 'priority') {
        return a.when.localeCompare(b.when) || b.p - a.p
      }

      const score = (r: typeof a) => r.p * 2 + r.expected * 12
      const scoreDiff = score(b) - score(a)
      if (Math.abs(scoreDiff) > 8) return scoreDiff
      return a.when.localeCompare(b.when) || scoreDiff
    })

    return list
  }, [latest.films, oddsByFilm, filter, today])

  const missing = latest.missing_films
  const stub = csvStub(missing)

  async function copyStub() {
    try {
      await navigator.clipboard.writeText(stub)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Releases</h2>
          <p className="lede">
            US dates from TMDB, ordered so strong Oscar contenders surface ahead
            of longshots — useful for planning what to catch next.
          </p>
        </div>
      </header>

      <div className="toolbar release-toolbar">
        <div className="pill-group" role="group" aria-label="Calendar filter">
          <button
            type="button"
            className={filter === 'priority' ? 'active' : ''}
            onClick={() => setFilter('priority')}
          >
            Priority contenders
          </button>
          <button
            type="button"
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All dated films
          </button>
        </div>
      </div>

      <div className="releases-layout">
        <div>
          <h3 className="section-title">
            Release calendar
            <span className="count">{dated.length}</span>
          </h3>
          {dated.length === 0 ? (
            <p className="empty">
              {filter === 'priority'
                ? 'No priority contenders have US dates yet — try All dated films.'
                : 'No US release dates found yet.'}
            </p>
          ) : (
            <ul className="release-list">
              {dated.map((f) => {
                const upcoming = isUpcoming(f.when, today)
                const weight =
                  f.p >= 80 ? 'hot' : f.p >= 40 ? 'warm' : f.p >= 15 ? 'cool' : 'cold'
                return (
                  <li
                    key={f.film}
                    className={`release-item ${weight} ${upcoming ? '' : 'past'}`}
                  >
                    <div className="film film-cell">
                      <PosterThumb url={f.poster_url} alt={f.film} size="md" />
                      <div className="release-main">
                        <div className="release-title-row">
                          <span className="release-title">{f.film}</span>
                          {f.certification ? (
                            <span className="cert">{f.certification}</span>
                          ) : null}
                        </div>
                        <div className="odds-line">
                          <span className="odds-p">{formatPct(f.p, 0)} ≥1 nom</span>
                          <span className="odds-e">
                            ~{formatExpected(f.expected)} expected
                          </span>
                          {f.watchRank < 9999 && (
                            <span className="odds-rank">#{f.watchRank} watch</span>
                          )}
                        </div>
                        <div className="meta">
                          {f.premiere_date && (
                            <span>Premiere {f.premiere_date}</span>
                          )}
                          {f.theatrical_date && (
                            <span>
                              Theaters {f.theatrical_date}
                              {f.theatrical_type ? ` · ${f.theatrical_type}` : ''}
                            </span>
                          )}
                          {f.streaming_date && (
                            <span>
                              Digital {f.streaming_date}
                              {f.streaming_platform
                                ? ` · ${f.streaming_platform}`
                                : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="missing-panel">
          <button
            type="button"
            className="missing-toggle"
            onClick={() => setShowMissing((v) => !v)}
            aria-expanded={showMissing}
          >
            <h3 className="section-title">
              Still needs attention
              <span className="count">{missing.length}</span>
            </h3>
            <span className="missing-chevron">{showMissing ? 'Hide' : 'Show'}</span>
          </button>
          {showMissing && (
            <div className="missing-body">
              {missing.length === 0 ? (
                <p className="empty">
                  Every tracked film has US release info from TMDB or a manual
                  row.
                </p>
              ) : (
                <>
                  <ol className="change-list">
                    {missing.map((film) => (
                      <li key={film}>
                        <span>{film}</span>
                      </li>
                    ))}
                  </ol>
                  <div className="missing-actions">
                    <button type="button" onClick={copyStub}>
                      {copied ? 'Copied' : 'Copy manual CSV stubs'}
                    </button>
                    <p className="hint">
                      Paste into <code>data/films.csv</code> with{' '}
                      <code>source=manual</code> to lock overrides.
                    </p>
                  </div>
                  <pre className="csv-preview">{stub}</pre>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
