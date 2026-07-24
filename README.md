# Oscars Predictions Dashboard

Track [Gold Derby](https://www.goldderby.com/) Oscars **nomination** odds over the season — not to invent predictions, but to watch how the race moves and decide what to watch.

**Live site:** https://mattheuscolyn.github.io/oscars-dashboard/

## What it answers

1. **Watch priority** — which films are most likely to earn at least one nomination (`P(≥1) ≈ 1 − ∏(1 − p_c)` across categories). Default source: **Combined**.
2. **Momentum** — how `P(≥1)` shifts over time; risers, fallers, and films that stayed in the top 10.
3. **By category** — nomination odds *within* a race (e.g. Best Picture) over time, plus current standings.
4. **Releases** — US theatrical / digital / premiere dates from [TMDB](https://developer.themoviedb.org/reference/search-movie), with a checklist for titles that still need attention.

Sources scraped daily:

- Users · Editors · Experts · Combined  
  `https://www.goldderby.com/odds/{user,editor,expert,combined}-odds/oscars-nominations-2027/`

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

# Optional for release enrichment
set TMDB_API_KEY=...
set TMDB_READ_ACCESS_TOKEN=...

python scrape.py          # writes data/snapshots/YYYY-MM-DD.json
python -m scraper.tmdb    # fills data/films.csv from TMDB US releases
python -m scraper.aggregate

cd web
npm install
npm run dev
```

Use `python scrape.py --force` to overwrite today’s snapshot. Use `--headed` to debug the browser.

## Release dates (TMDB)

The daily Action calls TMDB [search](https://developer.themoviedb.org/reference/search-movie) + [release dates](https://developer.themoviedb.org/reference/movie-release-dates) and keeps **United States** rows only:

| TMDB type | Stored as |
|-----------|-----------|
| Theatrical (limited) / Theatrical | `theatrical_date` + `theatrical_type` (`limited` / `wide`) |
| Digital | `streaming_date` + `streaming_platform` (from TMDB `note`) |
| Premiere | `premiere_date` |
| Certification | `certification` (e.g. R) |

Repo secrets: `TMDB_API_KEY`, `TMDB_READ_ACCESS_TOKEN`.

To lock a hand-edited row so TMDB won’t overwrite it, set `source=manual` in [`data/films.csv`](data/films.csv).

## Automation

| Workflow | Schedule | Role |
|----------|----------|------|
| `scrape.yml` | Daily 12:00 UTC (+ manual) | Scrape odds → TMDB enrich → update `data/` → push |
| `pages.yml` | On push to `main` | Aggregate → build Vite app → GitHub Pages |

## Repo layout

```
scraper/           Playwright scraper, TMDB enrich, aggregate
data/snapshots/    Daily JSON odds
data/films.csv     Release metadata (TMDB + manual overrides)
web/               Vite + React dashboard
```

Odds data belongs to Gold Derby; release metadata from TMDB. This project only stores snapshots for personal tracking.
