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
    """Expand each award's contender list, not the five individual contender cards.

    Every award contains several nested `expand__show-button` controls. The
    last one belongs to the award's "See All +" list. Iterating a global locator
    by index is unsafe: expanding one award adds new controls and shifts every
    later index, silently leaving most awards at five contenders.
    """
    awards = page.locator('[data-component="predictions-award-item"]')
    expanded = 0
    failures: list[str] = []

    for i in range(awards.count()):
        award = awards.nth(i)
        heading = award.locator("h1, h2, h3, h4, h5, h6").first
        name = (heading.text_content() or "").strip()
        items = award.locator('[data-component="predictions-contestant-item"]')
        before = items.count()

        # Contender detail controls precede this category-level See All button.
        show_all = award.locator('[data-alias="expand__show-button"] button').last
        if show_all.count() == 0 or not show_all.is_visible():
            print(f"    {name}: {before} entries (no collapsed list)")
            continue

        try:
            show_all.click(timeout=8_000)
        except Exception as exc:
            # A transient overlay can intercept a normal Playwright click.
            try:
                show_all.click(force=True, timeout=4_000)
            except Exception as retry_exc:
                failures.append(f"{name}: click failed ({retry_exc})")
                print(f"    {name}: See All click failed: {exc}")
                continue

        # Gold Derby loads the expanded contenders asynchronously. Do not move
        # on, or parse the page, until the additional DOM entries have arrived.
        try:
            page.wait_for_function(
                """({index, previousCount}) => {
                    const section = document.querySelectorAll(
                      '[data-component="predictions-award-item"]'
                    )[index];
                    return !!section && section.querySelectorAll(
                      '[data-component="predictions-contestant-item"]'
                    ).length > previousCount;
                }""",
                arg={"index": i, "previousCount": before},
                timeout=12_000,
            )
        except Exception:
            failures.append(f"{name}: still {items.count()} contenders after See All")
        after = items.count()
        print(f"    {name}: {before} -> {after} contenders")
        if after > before:
            expanded += 1

    if failures:
        raise RuntimeError(
            "Gold Derby contender lists were not fully expanded; refusing "
            "to save a truncated snapshot: " + "; ".join(failures)
        )
    return expanded


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
