# Oscars Predictions Dashboard

Track [Gold Derby](https://www.goldderby.com/) Oscars **nomination** odds over the season — not to invent predictions, but to watch how the race moves and decide what to watch.

**Live site:** https://mattheuscolyn.github.io/oscars-dashboard/

## What it answers

1. **Watch priority** — which films are most likely to earn at least one nomination (`P(≥1) ≈ 1 − ∏(1 − p_c)` across categories). Default source: **Combined**.
2. **Momentum** — risers, fallers, and films that stayed in the top 10.
3. **Releases** — theatrical / streaming dates you maintain by hand, plus a missing-data checklist.

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

python scrape.py          # writes data/snapshots/YYYY-MM-DD.json
python -m scraper.aggregate

cd web
npm install
npm run dev
```

Use `python scrape.py --force` to overwrite today’s snapshot. Use `--headed` to debug the browser.

## Adding release dates

1. Open the **Releases** tab on the site (or read `data/missing_films.csv` after a scrape).
2. Copy the CSV stub rows into [`data/films.csv`](data/films.csv).
3. Fill columns:

| Column | Notes |
|--------|--------|
| `film` | Must match the scraped title exactly |
| `theatrical_date` | ISO `YYYY-MM-DD` or blank |
| `theatrical_type` | `limited`, `wide`, or `tba` |
| `streaming_date` | ISO date or blank |
| `streaming_platform` | e.g. Netflix |
| `notes` | Optional |

4. Commit and push to `main`. The Pages build regenerates the site.

## Automation

| Workflow | Schedule | Role |
|----------|----------|------|
| `scrape.yml` | Daily 12:00 UTC (+ manual) | Scrape → update `data/` → push |
| `pages.yml` | On push to `main` | Aggregate → build Vite app → GitHub Pages |

Enable **Settings → Pages → Source: GitHub Actions** after the first push.

## Repo layout

```
scraper/           Playwright scraper + aggregate + missing-films
data/snapshots/    Daily JSON odds
data/films.csv     Manual release metadata
web/               Vite + React dashboard
```

Odds data belongs to Gold Derby; this project only stores snapshots for personal tracking.
