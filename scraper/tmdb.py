"""Enrich films.csv with United States release data from TMDB."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .films import (
    FILM_FIELDS,
    films_in_snapshot,
    load_films_csv,
    load_latest_snapshot,
    write_films_csv,
    write_missing_films,
)

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
FILMS_CSV = ROOT / "data" / "films.csv"
MISSING_CSV = ROOT / "data" / "missing_films.csv"

API_BASE = "https://api.themoviedb.org/3"

# Oscars 2027 eligibility is mostly 2026 theatrical releases
SEARCH_YEARS = ("2026", "2025", "2027", None)

# TMDB release types: https://developer.themoviedb.org/reference/movie-release-dates
TYPE_PREMIERE = 1
TYPE_THEATRICAL_LIMITED = 2
TYPE_THEATRICAL = 3
TYPE_DIGITAL = 4


def _auth_headers() -> dict[str, str]:
    token = (
        os.environ.get("TMDB_READ_ACCESS_TOKEN")
        or os.environ.get("TMDB_API_READ_ACCESS_TOKEN")
        or ""
    ).strip()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api_key() -> str:
    return (os.environ.get("TMDB_API_KEY") or "").strip()


def tmdb_get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    query = dict(params or {})
    api_key = _api_key()
    headers = _auth_headers()
    if "Authorization" not in headers:
        if not api_key:
            raise RuntimeError(
                "Set TMDB_READ_ACCESS_TOKEN and/or TMDB_API_KEY in the environment."
            )
        query["api_key"] = api_key
    elif api_key and "api_key" not in query:
        # Either auth method works; keep key as fallback for some gateways
        pass

    url = f"{API_BASE}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json

            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TMDB HTTP {e.code} for {path}: {body[:200]}") from e


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = t.replace("’", "'").replace("‘", "'")
    t = re.sub(r"[:\-–,]+", " ", t)
    t = re.sub(r"[^a-z0-9'& ]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Common article normalization
    if t.startswith("the "):
        t = t[4:]
    return t


def pick_search_result(query: str, results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not results:
        return None
    target = normalize_title(query)
    exact = []
    for r in results:
        titles = [
            r.get("title") or "",
            r.get("original_title") or "",
        ]
        if any(normalize_title(t) == target for t in titles if t):
            exact.append(r)
    pool = exact or results
    # Prefer higher popularity among matches
    pool = sorted(pool, key=lambda r: float(r.get("popularity") or 0), reverse=True)
    return pool[0]


def search_movie(title: str) -> dict[str, Any] | None:
    for year in SEARCH_YEARS:
        params: dict[str, str] = {
            "query": title,
            "include_adult": "false",
            "language": "en-US",
        }
        if year:
            params["primary_release_year"] = year
        data = tmdb_get("/search/movie", params)
        time.sleep(0.2)
        match = pick_search_result(title, data.get("results") or [])
        if match:
            return match
    return None


def parse_date(iso: str) -> str:
    if not iso:
        return ""
    return iso[:10]


def summarize_us_releases(release_payload: dict[str, Any]) -> dict[str, str]:
    """
    Collapse US release_dates into the columns we store in films.csv.
    Prefers earliest theatrical (wide over limited if same day not required —
    earliest limited, else earliest wide), earliest digital + note as platform,
    earliest premiere, and a non-empty certification from theatrical when possible.
    """
    us_entries: list[dict[str, Any]] = []
    for country in release_payload.get("results") or []:
        if country.get("iso_3166_1") == "US":
            us_entries = list(country.get("release_dates") or [])
            break

    premieres = [e for e in us_entries if e.get("type") == TYPE_PREMIERE]
    limited = [e for e in us_entries if e.get("type") == TYPE_THEATRICAL_LIMITED]
    wide = [e for e in us_entries if e.get("type") == TYPE_THEATRICAL]
    digital = [e for e in us_entries if e.get("type") == TYPE_DIGITAL]

    def earliest(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
        dated = [e for e in entries if e.get("release_date")]
        if not dated:
            return None
        return sorted(dated, key=lambda e: e["release_date"])[0]

    theatrical_type = ""
    theatrical_date = ""
    theatrical_cert = ""
    limited_e = earliest(limited)
    wide_e = earliest(wide)
    if limited_e and wide_e:
        # Use whichever comes first; type reflects that release
        if limited_e["release_date"] <= wide_e["release_date"]:
            theatrical_date = parse_date(limited_e["release_date"])
            theatrical_type = "limited"
            theatrical_cert = (limited_e.get("certification") or "").strip()
        else:
            theatrical_date = parse_date(wide_e["release_date"])
            theatrical_type = "wide"
            theatrical_cert = (wide_e.get("certification") or "").strip()
        # If limited precedes wide, still note wide date in notes? Keep primary as first theatrical.
    elif limited_e:
        theatrical_date = parse_date(limited_e["release_date"])
        theatrical_type = "limited"
        theatrical_cert = (limited_e.get("certification") or "").strip()
    elif wide_e:
        theatrical_date = parse_date(wide_e["release_date"])
        theatrical_type = "wide"
        theatrical_cert = (wide_e.get("certification") or "").strip()

    digital_e = earliest(digital)
    streaming_date = parse_date(digital_e["release_date"]) if digital_e else ""
    streaming_platform = (digital_e.get("note") or "").strip() if digital_e else ""

    premiere_e = earliest(premieres)
    premiere_date = parse_date(premiere_e["release_date"]) if premiere_e else ""

    # Certification: theatrical first, else any US cert
    certification = theatrical_cert
    if not certification:
        for e in us_entries:
            c = (e.get("certification") or "").strip()
            if c:
                certification = c
                break

    note_bits: list[str] = []
    if premiere_e and (premiere_e.get("note") or "").strip():
        note_bits.append(f"Premiere: {premiere_e['note'].strip()}")
    if limited_e and wide_e and limited_e["release_date"] != wide_e["release_date"]:
        other = wide_e if theatrical_type == "limited" else limited_e
        other_type = "wide" if theatrical_type == "limited" else "limited"
        note_bits.append(
            f"Also {other_type} {parse_date(other['release_date'])}"
        )

    return {
        "certification": certification,
        "premiere_date": premiere_date,
        "theatrical_date": theatrical_date,
        "theatrical_type": theatrical_type,
        "streaming_date": streaming_date,
        "streaming_platform": streaming_platform,
        "notes": "; ".join(note_bits),
    }


def empty_row(film: str) -> dict[str, str]:
    return {k: "" for k in FILM_FIELDS} | {"film": film, "source": ""}


def enrich_film(title: str, existing: dict[str, str] | None) -> dict[str, str]:
    row = empty_row(title)
    if existing:
        row.update({k: existing.get(k, "") for k in FILM_FIELDS})

    if (row.get("source") or "").strip().lower() == "manual":
        return row

    tmdb_id = (row.get("tmdb_id") or "").strip()
    match = None
    if tmdb_id:
        match = {"id": int(tmdb_id)}
    else:
        match = search_movie(title)
        if not match:
            row["source"] = "not_found"
            return row
        row["tmdb_id"] = str(match["id"])

    movie_id = int(row["tmdb_id"])
    releases = tmdb_get(f"/movie/{movie_id}/release_dates")
    time.sleep(0.2)
    summary = summarize_us_releases(releases)
    row.update(summary)
    row["source"] = "tmdb"
    return row


def enrich_all(limit: int | None = None) -> dict[str, int]:
    snapshot = load_latest_snapshot(SNAPSHOTS_DIR)
    if not snapshot:
        print("No snapshots found; nothing to enrich.")
        return {"updated": 0, "not_found": 0, "manual": 0, "total": 0}

    titles = sorted(films_in_snapshot(snapshot))
    if limit is not None:
        titles = titles[:limit]

    existing = load_films_csv(FILMS_CSV)
    updated_rows: dict[str, dict[str, str]] = dict(existing)
    stats = {"updated": 0, "not_found": 0, "manual": 0, "total": len(titles)}

    for i, title in enumerate(titles, 1):
        print(f"[{i}/{len(titles)}] {title}")
        try:
            row = enrich_film(title, existing.get(title))
        except Exception as e:
            print(f"  ERROR: {e}")
            row = existing.get(title) or empty_row(title)
            if not row.get("source"):
                row["source"] = "error"
        updated_rows[title] = row
        src = (row.get("source") or "").lower()
        if src == "manual":
            stats["manual"] += 1
        elif src == "not_found":
            stats["not_found"] += 1
            print("  not found on TMDB")
        else:
            stats["updated"] += 1
            print(
                f"  tmdb={row.get('tmdb_id')} "
                f"theatrical={row.get('theatrical_date') or '—'} "
                f"({row.get('theatrical_type') or '—'}) "
                f"digital={row.get('streaming_date') or '—'}"
            )

    # Keep any manual-only rows not in current odds
    write_films_csv(FILMS_CSV, updated_rows)
    missing = write_missing_films(SNAPSHOTS_DIR, FILMS_CSV, MISSING_CSV)
    print(f"Wrote {FILMS_CSV}")
    print(f"Missing release info: {len(missing)} -> {MISSING_CSV}")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich films.csv from TMDB US releases")
    parser.add_argument("--limit", type=int, default=None, help="Only process N films (debug)")
    args = parser.parse_args(argv)

    if not _api_key() and "Authorization" not in _auth_headers():
        print(
            "Missing TMDB credentials. Set TMDB_READ_ACCESS_TOKEN and/or TMDB_API_KEY.",
            file=sys.stderr,
        )
        return 1

    stats = enrich_all(limit=args.limit)
    print(
        f"Done. total={stats['total']} updated={stats['updated']} "
        f"not_found={stats['not_found']} manual={stats['manual']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
