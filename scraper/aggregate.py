"""Aggregate snapshots + films.csv into slim JSON for the dashboard."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
FILMS_CSV = ROOT / "data" / "films.csv"
OUT_DIR = ROOT / "web" / "public" / "data"

SOURCES = ("combined", "users", "editors", "experts")


def load_films(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    films: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("film") or "").strip()
            if name:
                films[name] = {
                    "film": name,
                    "theatrical_date": (row.get("theatrical_date") or "").strip(),
                    "theatrical_type": (row.get("theatrical_type") or "").strip(),
                    "streaming_date": (row.get("streaming_date") or "").strip(),
                    "streaming_platform": (row.get("streaming_platform") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                }
    return films


def load_snapshots(dir_path: Path) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(dir_path.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        out.append((path.stem, data))
    return out


def film_probs_for_source(
    categories: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, float]]:
    """Map film -> {category: pct/100} for a single source."""
    films: dict[str, dict[str, float]] = {}
    for category, entries in (categories or {}).items():
        for entry in entries or []:
            film = (entry.get("film") or "").strip()
            if not film:
                continue
            pct = float(entry.get("pct") or 0) / 100.0
            pct = max(0.0, min(1.0, pct))
            films.setdefault(film, {})
            # Keep max if duplicate rows for same film/category
            prev = films[film].get(category, 0.0)
            if pct >= prev:
                films[film][category] = pct
    return films


def watch_metrics(cat_probs: dict[str, float]) -> dict[str, Any]:
    if not cat_probs:
        return {
            "p_at_least_one": 0.0,
            "expected_noms": 0.0,
            "categories": [],
        }
    surv = 1.0
    expected = 0.0
    cats = []
    for cat, p in sorted(cat_probs.items(), key=lambda x: -x[1]):
        surv *= 1.0 - p
        expected += p
        cats.append({"category": cat, "pct": round(p * 100, 2)})
    p_at_least = 1.0 - surv
    # Guard floating point
    if math.isnan(p_at_least) or math.isinf(p_at_least):
        p_at_least = 0.0
    return {
        "p_at_least_one": round(p_at_least * 100, 2),
        "expected_noms": round(expected, 3),
        "categories": cats,
    }


def build_watch_priority(
    snapshot: dict[str, Any],
    films_meta: dict[str, dict[str, str]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    sources = snapshot.get("sources") or {}
    for source in SOURCES:
        film_probs = film_probs_for_source(sources.get(source) or {})
        rows = []
        for film, cat_probs in film_probs.items():
            metrics = watch_metrics(cat_probs)
            meta = films_meta.get(film, {})
            rows.append(
                {
                    "film": film,
                    "p_at_least_one": metrics["p_at_least_one"],
                    "expected_noms": metrics["expected_noms"],
                    "categories": metrics["categories"],
                    "theatrical_date": meta.get("theatrical_date", ""),
                    "theatrical_type": meta.get("theatrical_type", ""),
                    "streaming_date": meta.get("streaming_date", ""),
                    "streaming_platform": meta.get("streaming_platform", ""),
                    "notes": meta.get("notes", ""),
                    "has_metadata": film in films_meta,
                }
            )
        rows.sort(key=lambda r: (-r["p_at_least_one"], -r["expected_noms"], r["film"]))
        result[source] = rows
    return result


def build_history(
    snapshots: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """
    history.watch[source][film] = [{date, p_at_least_one, expected_noms}, ...]
    history.category[source][category][film] = [{date, pct, rank}, ...]
    """
    watch: dict[str, dict[str, list]] = {s: {} for s in SOURCES}
    category: dict[str, dict[str, dict[str, list]]] = {s: {} for s in SOURCES}
    dates: list[str] = []

    for date, snap in snapshots:
        dates.append(date)
        sources = snap.get("sources") or {}
        for source in SOURCES:
            cats = sources.get(source) or {}
            film_probs = film_probs_for_source(cats)
            for film, cat_probs in film_probs.items():
                m = watch_metrics(cat_probs)
                watch[source].setdefault(film, []).append(
                    {
                        "date": date,
                        "p_at_least_one": m["p_at_least_one"],
                        "expected_noms": m["expected_noms"],
                    }
                )

            for cat_name, entries in cats.items():
                category[source].setdefault(cat_name, {})
                for entry in entries or []:
                    film = (entry.get("film") or "").strip()
                    if not film:
                        continue
                    category[source][cat_name].setdefault(film, []).append(
                        {
                            "date": date,
                            "pct": float(entry.get("pct") or 0),
                            "rank": int(entry.get("rank") or 0),
                            "candidate": entry.get("candidate") or film,
                        }
                    )

    return {"dates": dates, "watch": watch, "category": category}


def build_latest_categories(snapshot: dict[str, Any]) -> dict[str, Any]:
    sources = snapshot.get("sources") or {}
    out: dict[str, Any] = {}
    for source in SOURCES:
        cats = sources.get(source) or {}
        out[source] = {
            cat: [
                {
                    "film": e.get("film"),
                    "candidate": e.get("candidate"),
                    "rank": e.get("rank"),
                    "pct": e.get("pct"),
                }
                for e in (entries or [])
            ]
            for cat, entries in cats.items()
        }
    return out


def aggregate() -> dict[str, Path]:
    snapshots = load_snapshots(SNAPSHOTS_DIR)
    films_meta = load_films(FILMS_CSV)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not snapshots:
        empty_latest = {
            "scraped_at": None,
            "season": "2027",
            "date": None,
            "watch_priority": {s: [] for s in SOURCES},
            "categories": {s: {} for s in SOURCES},
            "films": list(films_meta.values()),
            "missing_films": [],
        }
        empty_history = {
            "dates": [],
            "watch": {s: {} for s in SOURCES},
            "category": {s: {} for s in SOURCES},
        }
        latest_path = OUT_DIR / "latest.json"
        history_path = OUT_DIR / "history.json"
        latest_path.write_text(json.dumps(empty_latest, indent=2), encoding="utf-8")
        history_path.write_text(json.dumps(empty_history, indent=2), encoding="utf-8")
        return {"latest": latest_path, "history": history_path}

    date, latest_snap = snapshots[-1]
    watch_priority = build_watch_priority(latest_snap, films_meta)
    categories = build_latest_categories(latest_snap)

    all_films: set[str] = set()
    for source_rows in watch_priority.values():
        for row in source_rows:
            all_films.add(row["film"])
    missing = sorted(all_films - set(films_meta.keys()))

    latest = {
        "scraped_at": latest_snap.get("scraped_at"),
        "season": latest_snap.get("season", "2027"),
        "date": date,
        "watch_priority": watch_priority,
        "categories": categories,
        "films": list(films_meta.values()),
        "missing_films": missing,
    }

    history = build_history(snapshots)

    latest_path = OUT_DIR / "latest.json"
    history_path = OUT_DIR / "history.json"
    latest_path.write_text(
        json.dumps(latest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    history_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {latest_path}")
    print(f"Wrote {history_path}")
    print(f"  date={date}, missing_films={len(missing)}")
    return {"latest": latest_path, "history": history_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate Oscar odds for the web app")
    parser.parse_args(argv)
    aggregate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
