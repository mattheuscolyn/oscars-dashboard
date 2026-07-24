import { useState } from 'react'
import { ByCategory } from './components/ByCategory'
import { Momentum } from './components/Momentum'
import { Releases } from './components/Releases'
import { WatchPriority } from './components/WatchPriority'
import type { SourceKey } from './types'
import { useDashboardData } from './useData'
import './App.css'

type Tab = 'watch' | 'momentum' | 'category' | 'releases'

const TABS: { id: Tab; label: string; short: string }[] = [
  { id: 'watch', label: 'Watch priority', short: 'Watch' },
  { id: 'momentum', label: 'Momentum', short: 'Momentum' },
  { id: 'category', label: 'By category', short: 'Category' },
  { id: 'releases', label: 'Releases', short: 'Releases' },
]

export default function App() {
  const { latest, history, error, loading } = useDashboardData()
  const [tab, setTab] = useState<Tab>('watch')
  const [source, setSource] = useState<SourceKey>('combined')

  return (
    <div className="app">
      <div className="grain" aria-hidden />
      <header className="site-header">
        <p className="eyebrow">Gold Derby · Nominations</p>
        <h1>Oscars {latest?.season ?? '2027'}</h1>
        <p className="tagline">
          Daily odds from users, editors, experts, and combined — tracked so you
          can decide what to watch while the race is still wild.
        </p>
        <p className="meta-line">
          {latest?.date
            ? `Latest scrape ${latest.date}${
                latest.scraped_at
                  ? ` · ${new Date(latest.scraped_at).toUTCString()}`
                  : ''
              }`
            : 'No snapshots yet — run the scraper or wait for the daily Action.'}
          {latest && latest.missing_films.length > 0 && (
            <>
              {' '}
              ·{' '}
              <button
                type="button"
                className="text-link"
                onClick={() => setTab('releases')}
              >
                {latest.missing_films.length} films missing release data
              </button>
            </>
          )}
        </p>
      </header>

      <nav className="tabs" aria-label="Dashboard sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            <span className="tab-full">{t.label}</span>
            <span className="tab-short">{t.short}</span>
          </button>
        ))}
      </nav>

      <main>
        {loading && <p className="status">Loading odds…</p>}
        {error && (
          <p className="status error">
            Could not load data ({error}). Run{' '}
            <code>python -m scraper.aggregate</code> then rebuild.
          </p>
        )}
        {!loading && !error && latest && history && (
          <>
            {tab === 'watch' && (
              <WatchPriority
                latest={latest}
                source={source}
                onSourceChange={setSource}
              />
            )}
            {tab === 'momentum' && (
              <Momentum
                latest={latest}
                history={history}
                source={source}
                onSourceChange={setSource}
              />
            )}
            {tab === 'category' && (
              <ByCategory
                latest={latest}
                history={history}
                source={source}
                onSourceChange={setSource}
              />
            )}
            {tab === 'releases' && (
              <Releases latest={latest} source={source} />
            )}
          </>
        )}
      </main>

      <footer className="site-footer">
        <p>
          Odds © Gold Derby. This site only aggregates public nomination
          probabilities for personal tracking.
        </p>
      </footer>
    </div>
  )
}
