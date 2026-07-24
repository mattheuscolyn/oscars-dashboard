"""Scrape Gold Derby Oscars nomination odds from all four sources."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from .films import write_missing_films
from .parse import extract_source_odds

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
FILMS_CSV = ROOT / "data" / "films.csv"
MISSING_CSV = ROOT / "data" / "missing_films.csv"

SEASON = "2027"

SOURCES = {
    "users": f"https://www.goldderby.com/odds/user-odds/oscars-nominations-{SEASON}/",
    "editors": f"https://www.goldderby.com/odds/editor-odds/oscars-nominations-{SEASON}/",
    "experts": f"https://www.goldderby.com/odds/expert-odds/oscars-nominations-{SEASON}/",
    "combined": f"https://www.goldderby.com/odds/combined-odds/oscars-nominations-{SEASON}/",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def expand_all_categories(page) -> int:
    """Click Gold Derby 'See All +' buttons so collapsed longlists load."""
    buttons = page.locator(
        '[data-component="predictions-award-item"] [data-alias="expand__show-button"]'
    )
    count = buttons.count()
    clicked = 0
    for i in range(count):
        try:
            btn = buttons.nth(i)
            if btn.is_visible():
                btn.click(timeout=2000)
                clicked += 1
                page.wait_for_timeout(250)
        except Exception:
            continue
    if clicked:
        page.wait_for_timeout(1500)
    return clicked


def scrape_all(headless: bool = True) -> dict:
    scraped_at = datetime.now(timezone.utc).isoformat()
    sources_data: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(60_000)

        for source_key, url in SOURCES.items():
            print(f"Scraping {source_key}: {url}")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            body_len = len(page.inner_text("body") or "")
            if body_len < 500:
                print(f"  Page looks thin ({body_len} chars), waiting longer...")
                page.wait_for_timeout(5000)

            page.wait_for_selector(
                '[data-component="predictions-contestant-item"]',
                timeout=60_000,
            )
            expanded = expand_all_categories(page)
            print(f"  Expanded {expanded} category lists")

            categories = extract_source_odds(page)
            n_entries = sum(len(v) for v in categories.values())
            print(f"  Found {len(categories)} categories, {n_entries} entries")

            if not categories:
                browser.close()
                raise RuntimeError(
                    f"Source '{source_key}' returned zero categories. "
                    "Selectors may be broken."
                )

            sources_data[source_key] = categories

        browser.close()

    return {
        "scraped_at": scraped_at,
        "season": SEASON,
        "sources": sources_data,
    }


def save_snapshot(data: dict, force: bool = False) -> Path:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = SNAPSHOTS_DIR / f"{today}.json"

    if path.exists() and not force:
        print(f"Snapshot already exists: {path} (use --force to overwrite)")
        return path

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scrape Gold Derby Oscars nomination odds"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite today's snapshot if it already exists",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser headed (for debugging)",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Do not regenerate missing_films.csv",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print(f"Gold Derby Oscars Nominations {SEASON} Scraper")
    print("=" * 60)

    data = scrape_all(headless=not args.headed)
    path = save_snapshot(data, force=args.force)

    if not args.skip_missing:
        missing = write_missing_films(SNAPSHOTS_DIR, FILMS_CSV, MISSING_CSV)
        print(f"Missing film metadata: {len(missing)} titles -> {MISSING_CSV}")

    # Summary
    for source, cats in data["sources"].items():
        n = sum(len(v) for v in cats.values())
        print(f"  {source}: {len(cats)} categories, {n} entries")

    print(f"Done. Snapshot: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
