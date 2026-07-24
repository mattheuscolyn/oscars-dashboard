import { useMemo, useState } from 'react'
import type { LatestData } from '../types'
import { csvStub } from '../utils'
import { PosterThumb } from './PosterThumb'

interface Props {
  latest: LatestData
}

export function Releases({ latest }: Props) {
  const [copied, setCopied] = useState(false)

  const dated = useMemo(() => {
    return [...latest.films]
      .filter((f) => f.theatrical_date || f.streaming_date || f.premiere_date)
      .sort((a, b) => {
        const da =
          a.theatrical_date || a.streaming_date || a.premiere_date || '9999'
        const db =
          b.theatrical_date || b.streaming_date || b.premiere_date || '9999'
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
            US release dates are pulled from{' '}
            <a
              href="https://developer.themoviedb.org/reference/movie-release-dates"
              target="_blank"
              rel="noreferrer"
            >
              TMDB
            </a>{' '}
            during the daily scrape (theatrical limited/wide, digital, premiere).
            Override any row in <code>data/films.csv</code> by setting{' '}
            <code>source=manual</code>. Films TMDB can’t match, or that still
            have no US dates, appear below.
          </p>
        </div>
      </header>

      <div className="split-lists releases-split">
        <div>
          <h3>Release calendar</h3>
          {dated.length === 0 ? (
            <p className="empty">No US release dates found yet.</p>
          ) : (
            <ul className="release-list">
              {dated.map((f) => (
                <li key={f.film}>
                  <div className="film film-cell">
                    <PosterThumb url={f.poster_url} alt={f.film} size="md" />
                    <span>
                      {f.film}
                      {f.certification ? (
                        <span className="cert"> {f.certification}</span>
                      ) : null}
                    </span>
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
                    {f.notes && <span className="notes">{f.notes}</span>}
                    {f.tmdb_id && (
                      <span>
                        <a
                          href={`https://www.themoviedb.org/movie/${f.tmdb_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          TMDB
                        </a>
                        {f.source ? ` · ${f.source}` : ''}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3>
            Still needs attention{' '}
            <span className="count">{missing.length}</span>
          </h3>
          {missing.length === 0 ? (
            <p className="empty">
              Every tracked film has US release info from TMDB or a manual row.
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
                  <code>source=manual</code> to lock overrides (TMDB won’t
                  overwrite them).
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
