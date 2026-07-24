"""Generate missing-films report by diffing snapshots against films.csv."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


FILM_FIELDS = [
    "film",
    "theatrical_date",
    "theatrical_type",
    "streaming_date",
    "streaming_platform",
    "notes",
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
    return films


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


def write_missing_films(
    snapshots_dir: Path,
    films_csv: Path,
    out_path: Path,
) -> list[str]:
    snapshot = load_latest_snapshot(snapshots_dir)
    if not snapshot:
        out_path.write_text(
            ",".join(FILM_FIELDS) + "\n",
            encoding="utf-8",
        )
        return []

    known = load_films_csv(films_csv)
    scraped = films_in_snapshot(snapshot)
    missing = sorted(scraped - set(known.keys()))

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FILM_FIELDS)
        writer.writeheader()
        for film in missing:
            writer.writerow(
                {
                    "film": film,
                    "theatrical_date": "",
                    "theatrical_type": "",
                    "streaming_date": "",
                    "streaming_platform": "",
                    "notes": "",
                }
            )
    return missing
