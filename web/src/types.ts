export type SourceKey = 'combined' | 'users' | 'editors' | 'experts'

export interface CategoryPct {
  category: string
  pct: number
}

export interface WatchRow {
  film: string
  p_at_least_one: number
  expected_noms: number
  categories: CategoryPct[]
  tmdb_id: string
  poster_path: string
  poster_url: string
  certification: string
  premiere_date: string
  theatrical_date: string
  theatrical_type: string
  streaming_date: string
  streaming_platform: string
  notes: string
  source: string
  has_metadata: boolean
}

export interface Contestant {
  film: string
  candidate: string
  rank: number
  pct: number
}

export interface FilmMeta {
  film: string
  tmdb_id: string
  poster_path: string
  poster_url: string
  certification: string
  premiere_date: string
  theatrical_date: string
  theatrical_type: string
  streaming_date: string
  streaming_platform: string
  notes: string
  source: string
}

export interface LatestData {
  scraped_at: string | null
  season: string
  date: string | null
  watch_priority: Record<SourceKey, WatchRow[]>
  categories: Record<SourceKey, Record<string, Contestant[]>>
  films: FilmMeta[]
  missing_films: string[]
}

export interface HistoryPoint {
  date: string
  p_at_least_one: number
  expected_noms: number
}

export interface CategoryHistoryPoint {
  date: string
  pct: number
  rank: number
  candidate: string
}

export interface HistoryData {
  dates: string[]
  watch: Record<SourceKey, Record<string, HistoryPoint[]>>
  category: Record<
    SourceKey,
    Record<string, Record<string, CategoryHistoryPoint[]>>
  >
}

export const SOURCE_LABELS: Record<SourceKey, string> = {
  combined: 'Combined',
  experts: 'Experts',
  editors: 'Editors',
  users: 'Users',
}

export const SOURCES: SourceKey[] = [
  'combined',
  'experts',
  'editors',
  'users',
]
