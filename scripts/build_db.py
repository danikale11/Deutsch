#!/usr/bin/env python3
"""A data/history/*.json fajlokbol (napi eredmenyek) ujraepiti:
  - data/app.db          : lekerdezheto/letoltheto SQLite adatbazis
  - data/history_index.json : kompakt osszesito a frontend history
                               nezetehez + gyenge-tema statisztika a
                               generate_daily.py sulyozasahoz

Hasznalat:
    python3 scripts/build_db.py
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DATA_DIR = REPO_ROOT / "web" / "data"
HISTORY_DIR = WEB_DATA_DIR / "history"
DB_PATH = WEB_DATA_DIR / "app.db"
HISTORY_INDEX_PATH = WEB_DATA_DIR / "history_index.json"

CATEGORIES = ["hu_de_sentences", "de_hu_sentences", "hu_de_vocab", "de_hu_vocab"]


def load_history_files() -> list[dict]:
    if not HISTORY_DIR.exists():
        return []
    records = []
    for path in sorted(HISTORY_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            records.append(json.load(fh))
    return records


def rebuild_sqlite(records: list[dict]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE attempts (
                date TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                timestamp TEXT,
                points REAL,
                max_points REAL,
                percent REAL,
                PRIMARY KEY (date, attempt_no)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE answers (
                date TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                category TEXT NOT NULL,
                item_id TEXT,
                direction TEXT,
                topic TEXT,
                tier TEXT,
                points REAL,
                user_answer TEXT
            )
            """
        )

        for record in records:
            record_date = record.get("date")
            for attempt in record.get("attempts", []):
                attempt_no = attempt.get("attempt_no")
                score = attempt.get("score", {})
                conn.execute(
                    "INSERT INTO attempts (date, attempt_no, timestamp, points, max_points, percent) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        record_date,
                        attempt_no,
                        attempt.get("timestamp"),
                        score.get("points"),
                        score.get("max"),
                        score.get("percent"),
                    ),
                )
                answers = attempt.get("answers", {})
                for category in CATEGORIES:
                    for task_answer in answers.get(category, []):
                        conn.execute(
                            "INSERT INTO answers (date, attempt_no, category, item_id, direction, "
                            "topic, tier, points, user_answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                record_date,
                                attempt_no,
                                category,
                                task_answer.get("id"),
                                task_answer.get("direction"),
                                task_answer.get("topic"),
                                task_answer.get("tier"),
                                task_answer.get("points"),
                                task_answer.get("user_answer"),
                            ),
                        )
        conn.commit()
    finally:
        conn.close()


def compute_streak(days_with_attempts: set[date]) -> int:
    if not days_with_attempts:
        return 0
    most_recent = max(days_with_attempts)
    # a streak-et akkor is szamoljuk, ha a legutolso nap a tegnap volt
    # (meg nem csinaltuk meg a mait), de nem, ha regebbi 1 napnal.
    if (date.today() - most_recent).days > 1:
        return 0
    streak = 0
    cursor = most_recent
    while cursor in days_with_attempts:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_topic_stats(records: list[dict]) -> dict[str, dict]:
    stats: dict[str, dict[str, int]] = {}
    for record in records:
        for attempt in record.get("attempts", []):
            answers = attempt.get("answers", {})
            for category in CATEGORIES:
                for task_answer in answers.get(category, []):
                    topic = task_answer.get("topic")
                    if not topic:
                        continue
                    entry = stats.setdefault(topic, {"attempts": 0, "incorrect": 0})
                    entry["attempts"] += 1
                    tier = task_answer.get("tier")
                    if tier == "incorrect":
                        entry["incorrect"] += 1
                    elif tier == "partial":
                        entry["incorrect"] += 0.5
    return {
        topic: {
            "attempts": v["attempts"],
            "incorrect": v["incorrect"],
            "error_rate": (v["incorrect"] / v["attempts"]) if v["attempts"] else 0,
        }
        for topic, v in stats.items()
    }


def compute_history_index(records: list[dict]) -> dict:
    days_summary = []
    days_with_attempts: set[date] = set()

    for record in sorted(records, key=lambda r: r.get("date", ""), reverse=True):
        record_date = record.get("date")
        attempts = record.get("attempts", [])
        if not attempts:
            continue
        try:
            days_with_attempts.add(date.fromisoformat(record_date))
        except (TypeError, ValueError):
            pass

        last_attempt = attempts[-1]
        best_attempt = max(
            attempts, key=lambda a: a.get("score", {}).get("percent", 0)
        )
        days_summary.append(
            {
                "date": record_date,
                "attempt_count": len(attempts),
                "last_score": last_attempt.get("score"),
                "best_score": best_attempt.get("score"),
            }
        )

    streak = compute_streak(days_with_attempts)
    topic_stats = compute_topic_stats(records)

    total_attempts = sum(d["attempt_count"] for d in days_summary)
    avg_percent = None
    if days_summary:
        percents = [
            d["last_score"]["percent"]
            for d in days_summary
            if d.get("last_score") and d["last_score"].get("percent") is not None
        ]
        if percents:
            avg_percent = sum(percents) / len(percents)

    return {
        "generated_at": date.today().isoformat(),
        "days": days_summary,
        "streak_days": streak,
        "total_days_practiced": len(days_summary),
        "total_attempts": total_attempts,
        "average_percent": avg_percent,
        "topic_stats": topic_stats,
    }


def main() -> None:
    records = load_history_files()
    rebuild_sqlite(records)
    index = compute_history_index(records)
    HISTORY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_INDEX_PATH.open("w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
    print(
        f"Ujraepitve: {DB_PATH} es {HISTORY_INDEX_PATH} "
        f"({len(records)} nap, {index['total_attempts']} probalkozas)"
    )


if __name__ == "__main__":
    main()
