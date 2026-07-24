"""Parse Gold Derby predictions DOM into structured contestant rows."""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page

PEOPLE_CATEGORIES = {
    "Best Actor",
    "Best Actress",
    "Best Supporting Actor",
    "Best Supporting Actress",
    "Best Director",
}

# Categories where the title is the creative work, not the film
SPECIAL_TITLE_IS_FILM = {
    "Best Song",  # title = film, subtitle = song name on Gold Derby
}


def _safe_text(locator) -> str:
    try:
        text = (locator.inner_text(timeout=500) or "").strip()
        if text:
            return text
    except Exception:
        pass
    try:
        return (locator.text_content(timeout=500) or "").strip()
    except Exception:
        return ""


def _parse_pct(raw: str) -> float:
    match = re.search(r"([\d.]+)", raw or "")
    if not match:
        return 0.0
    return float(match.group(1))


def _parse_rank(raw: str) -> int:
    match = re.search(r"(\d+)", raw or "")
    if not match:
        return 0
    return int(match.group(1))


def extract_source_odds(page: Page) -> dict[str, list[dict[str, Any]]]:
    """
    Extract contestants grouped by category from a loaded odds page.

    Returns:
        { "Best Picture": [ {film, candidate, rank, pct}, ... ], ... }
    """
    page.wait_for_selector(
        '[data-component="predictions-contestant-item"]',
        timeout=60_000,
    )

    # Prefer structured award sections when present
    award_items = page.locator('[data-component="predictions-award-item"]')
    count = award_items.count()
    result: dict[str, list[dict[str, Any]]] = {}

    if count > 0:
        for i in range(count):
            award = award_items.nth(i)
            heading = award.locator("h1, h2, h3, h4, h5, h6").first
            category = _safe_text(heading)
            if not category or "Best" not in category:
                continue

            entries: list[dict[str, Any]] = []
            items = award.locator('[data-component="predictions-contestant-item"]')
            for j in range(items.count()):
                entry = _parse_contestant(items.nth(j), category)
                if entry:
                    entries.append(entry)
            if entries:
                result[category] = entries
        return result

    # Fallback: flat contestant list with last-known category
    items = page.locator('[data-component="predictions-contestant-item"]')
    last_category = "Unknown"
    for j in range(items.count()):
        item = items.nth(j)
        category = last_category
        try:
            award = item.locator(
                'xpath=ancestor::*[@data-component="predictions-award-item"]'
            ).first
            heading = award.locator("h1, h2, h3, h4, h5, h6").first
            cat_text = _safe_text(heading)
            if cat_text:
                category = cat_text
                last_category = cat_text
        except Exception:
            pass

        entry = _parse_contestant(item, category)
        if not entry or category == "Unknown":
            continue
        result.setdefault(category, []).append(entry)

    return result


def _parse_contestant(item, category: str) -> dict[str, Any] | None:
    index_el = item.locator(
        'span[class*="contestantIndex"], [data-alias="predictions-contestant-item__index"]'
    ).first
    # Gold Derby uses hashed class names; try several selectors
    if index_el.count() == 0:
        index_el = item.locator("span").first

    rank_text = _safe_text(index_el)
    # Prefer dedicated index span if present in DOM
    try:
        alt = item.locator("span").filter(has_text=re.compile(r"^\d+$"))
        if alt.count() > 0:
            rank_text = _safe_text(alt.first) or rank_text
    except Exception:
        pass

    # More reliable: evaluate ranking from the contestant index node used historically
    try:
        rank_js = item.evaluate(
            """(el) => {
              const idx = el.querySelector('span[class*="contestantIndex"]')
                || el.querySelector('[data-alias="predictions-contestant-item__index"]');
              return idx ? (idx.textContent || '').trim() : '';
            }"""
        )
        if rank_js:
            rank_text = rank_js
    except Exception:
        pass

    rank = _parse_rank(rank_text)
    if rank <= 0:
        return None

    title_el = item.locator('[data-alias="predictions-contestant-item__title"]').first
    name = _safe_text(title_el)
    if not name:
        return None

    subtitle = ""
    try:
        sub_el = item.locator(
            '[data-alias="predictions-contestant-item__sub-title"]'
        ).first
        if sub_el.count() > 0:
            subtitle = _safe_text(sub_el)
    except Exception:
        pass

    pct_raw = "0%"
    try:
        pct_el = item.locator(
            '[data-alias="predictions-contestant-item__progress-text"]'
        ).first
        if pct_el.count() > 0:
            pct_raw = _safe_text(pct_el) or pct_raw
    except Exception:
        pass

    # Resolve film vs candidate
    # People categories: title = person, subtitle = film
    # Film categories: title = film
    # Best Song: title = film (per original scraper)
    if category in PEOPLE_CATEGORIES and subtitle:
        candidate = name
        film = subtitle
    elif category in SPECIAL_TITLE_IS_FILM:
        candidate = subtitle or name
        film = name
    elif subtitle and category not in PEOPLE_CATEGORIES:
        # Some film categories duplicate title in subtitle
        candidate = name
        film = name
    else:
        candidate = name
        film = name

    # Strip wrapping quotes/curly quotes sometimes present on titles
    quotes = "\"'" + "\u201c\u201d\u2018\u2019"
    film = film.strip().strip(quotes)
    candidate = candidate.strip().strip(quotes)

    return {
        "film": film,
        "candidate": candidate,
        "rank": rank,
        "pct": _parse_pct(pct_raw),
    }
