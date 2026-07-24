"""Film metadata CSV helpers and missing-films report."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


FILM_FIELDS = [
    "film",
    "tmdb_id",
    "certification",
    "premiere_date",
    "theatrical_date",
    "theatrical_type",
    "streaming_date",
    "streaming_platform",
    "notes",
    "source",
]


def load_films_csv(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    films: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("film") or "").strip()
            if name:
                films[name] = {k: (row.get(k) or "").strip() for k in FILM_FIELDS}
                films[name]["film"] = name
    return films


def write_films_csv(path: Path, films: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FILM_FIELDS)
        writer.writeheader()
        for name in sorted(films.keys(), key=lambda s: s.lower()):
            row = {k: (films[name].get(k) or "") for k in FILM_FIELDS}
            row["film"] = name
            writer.writerow(row)


def films_in_snapshot(snapshot: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    sources = snapshot.get("sources") or {}
    for categories in sources.values():
        if not isinstance(categories, dict):
            continue
        for entries in categories.values():
            for entry in entries or []:
                film = (entry.get("film") or "").strip()
                if film:
                    names.add(film)
    return names


def load_latest_snapshot(snapshots_dir: Path) -> dict[str, Any] | None:
    files = sorted(snapshots_dir.glob("*.json"))
    if not files:
        return None
    with files[-1].open(encoding="utf-8") as f:
        return json.load(f)


def has_release_info(row: dict[str, str]) -> bool:
    return bool(
        (row.get("theatrical_date") or "").strip()
        or (row.get("streaming_date") or "").strip()
        or (row.get("premiere_date") or "").strip()
    )


def write_missing_films(
    snapshots_dir: Path,
    films_csv: Path,
    out_path: Path,
) -> list[str]:
    """
    Films in the latest odds snapshot that still need attention:
    no CSV row, TMDB not_found, or matched but no US release dates yet.
    """
    snapshot = load_latest_snapshot(snapshots_dir)
    if not snapshot:
        out_path.write_text(",".join(FILM_FIELDS) + "\n", encoding="utf-8")
        return []

    known = load_films_csv(films_csv)
    scraped = films_in_snapshot(snapshot)
    missing: list[str] = []
    for film in sorted(scraped):
        row = known.get(film)
        if not row:
            missing.append(film)
            continue
        source = (row.get("source") or "").lower()
        if source in {"not_found", "error"} or not has_release_info(row):
            missing.append(film)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FILM_FIELDS)
        writer.writeheader()
        for film in missing:
            base = known.get(film) or {k: "" for k in FILM_FIELDS}
            row = {k: (base.get(k) or "") for k in FILM_FIELDS}
            row["film"] = film
            writer.writerow(row)
    return missing
