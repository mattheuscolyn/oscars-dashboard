import { useMemo, useState } from 'react'
import type { LatestData } from '../types'
import { csvStub } from '../utils'

interface Props {
  latest: LatestData
}

export function Releases({ latest }: Props) {
  const [copied, setCopied] = useState(false)

  const dated = useMemo(() => {
    return [...latest.films]
      .filter((f) => f.theatrical_date || f.streaming_date)
      .sort((a, b) => {
        const da = a.theatrical_date || a.streaming_date || '9999'
        const db = b.theatrical_date || b.streaming_date || '9999'
        return da.localeCompare(db)
      })
  }, [latest.films])

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
          <h2>Releases &amp; missing data</h2>
          <p className="lede">
            Release dates are maintained manually in{' '}
            <code>data/films.csv</code>. Films that appear in Gold Derby odds
            but lack a row show up below — research them, paste stub rows into
            the CSV, commit, and the next build picks them up.
          </p>
        </div>
      </header>

      <div className="split-lists releases-split">
        <div>
          <h3>Release calendar</h3>
          {dated.length === 0 ? (
            <p className="empty">No release dates entered yet.</p>
          ) : (
            <ul className="release-list">
              {dated.map((f) => (
                <li key={f.film}>
                  <div className="film">{f.film}</div>
                  <div className="meta">
                    {f.theatrical_date && (
                      <span>
                        Theaters {f.theatrical_date}
                        {f.theatrical_type ? ` · ${f.theatrical_type}` : ''}
                      </span>
                    )}
                    {f.streaming_date && (
                      <span>
                        Streaming {f.streaming_date}
                        {f.streaming_platform
                          ? ` · ${f.streaming_platform}`
                          : ''}
                      </span>
                    )}
                    {f.notes && <span className="notes">{f.notes}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3>
            Missing metadata{' '}
            <span className="count">{missing.length}</span>
          </h3>
          {missing.length === 0 ? (
            <p className="empty">All tracked films have a films.csv row.</p>
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
                  {copied ? 'Copied' : 'Copy CSV stub rows'}
                </button>
                <p className="hint">
                  Paste into <code>data/films.csv</code>, fill dates (
                  <code>limited</code> / <code>wide</code> / <code>tba</code>),
                  then push to main.
                </p>
              </div>
              <pre className="csv-preview">{stub}</pre>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
