#!/usr/bin/env python3
"""Napi feladatsor gyartasa: 5 HU->DE mondat, 5 DE->HU mondat,
5 HU->DE szopár, 5 DE->HU szopár, megoldassal es magyarazattal.

Hasznalat:
    python3 scripts/generate_daily.py

Kimenet:
    data/daily/today.json    - a mai feladatsor
    data/state/usage_state.json - frissitett hasznalati elozmeny
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import pool as pool_lib  # noqa: E402
from lib import explanations  # noqa: E402

TIMEZONE = ZoneInfo("Europe/Budapest")
WEB_DATA_DIR = REPO_ROOT / "web" / "data"
STATE_PATH = WEB_DATA_DIR / "state" / "usage_state.json"
DAILY_PATH = WEB_DATA_DIR / "daily" / "today.json"
HISTORY_INDEX_PATH = WEB_DATA_DIR / "history_index.json"

ITEMS_PER_CATEGORY = 5


def load_weak_topics() -> dict[str, float] | None:
    """A build_db.py altal frissitett history_index.json-bol olvassa ki a
    gyenge temak hibaaranyat, ha van ilyen adat. Ha nincs history meg,
    None-t ad vissza (nincs sulyozas)."""
    if not HISTORY_INDEX_PATH.exists():
        return None
    try:
        with HISTORY_INDEX_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None

    topic_stats = data.get("topic_stats")
    if not topic_stats:
        return None

    weak: dict[str, float] = {}
    for topic, stats in topic_stats.items():
        attempts = stats.get("attempts", 0)
        incorrect = stats.get("incorrect", 0)
        if attempts >= 3:  # csak eleg adat eseten vegyunk figyelembe egy temat
            weak[topic] = incorrect / attempts
    return weak or None


def build_sentence_task(item: dict, direction: str) -> dict:
    if direction == "hu_de":
        prompt, solution = item["hu"], item["de"]
    else:
        prompt, solution = item["de"], item["hu"]
    return {
        "id": item["id"],
        "direction": direction,
        "prompt": prompt,
        "solution": solution,
        "explanation": explanations.sentence_explanation(item),
        "topic": item.get("topic"),
        "chapter_title": item.get("chapter_title"),
        "source": item["source"],
    }


def build_vocab_task(item: dict, direction: str) -> dict:
    if direction == "hu_de":
        prompt, solution = item["hu"], item["de"]
    else:
        prompt, solution = item["de"], item["hu"]
    return {
        "id": item["id"],
        "direction": direction,
        "prompt": prompt,
        "solution": solution,
        "note": explanations.vocab_note(item),
        "topic": item.get("topic"),
        "pos": item.get("pos"),
        "source": item["source"],
    }


def main() -> None:
    rng = random.Random()
    today = datetime.now(TIMEZONE).date()

    pool = pool_lib.load_pool()
    usage_state = pool_lib.load_usage_state(STATE_PATH)
    weak_topics = load_weak_topics()

    # --- mondatok kivalasztasa ---
    sentence_candidates = pool_lib.filter_by_cooldown(
        pool.sentences, usage_state, today, min_pool_size=ITEMS_PER_CATEGORY * 2
    )
    hu_de_sentences = pool_lib.weighted_sample_without_replacement(
        sentence_candidates, ITEMS_PER_CATEGORY, weak_topics, rng
    )
    used_ids = {it["id"] for it in hu_de_sentences}
    remaining_sentences = [it for it in sentence_candidates if it["id"] not in used_ids]
    if len(remaining_sentences) < ITEMS_PER_CATEGORY:
        # ha kifogytunk, engedjuk vissza a teljes poolbol (mar hasznaltakat is)
        remaining_sentences = [it for it in pool.sentences if it["id"] not in used_ids]
    de_hu_sentences = pool_lib.weighted_sample_without_replacement(
        remaining_sentences, ITEMS_PER_CATEGORY, weak_topics, rng
    )

    # --- szoparok kivalasztasa ---
    vocab_candidates = pool_lib.filter_by_cooldown(
        pool.vocab, usage_state, today, min_pool_size=ITEMS_PER_CATEGORY * 2
    )
    hu_de_vocab = pool_lib.weighted_sample_without_replacement(
        vocab_candidates, ITEMS_PER_CATEGORY, weak_topics, rng
    )
    used_vocab_ids = {it["id"] for it in hu_de_vocab}
    remaining_vocab = [it for it in vocab_candidates if it["id"] not in used_vocab_ids]
    if len(remaining_vocab) < ITEMS_PER_CATEGORY:
        remaining_vocab = [it for it in pool.vocab if it["id"] not in used_vocab_ids]
    de_hu_vocab = pool_lib.weighted_sample_without_replacement(
        remaining_vocab, ITEMS_PER_CATEGORY, weak_topics, rng
    )

    daily = {
        "date": today.isoformat(),
        "generated_at": datetime.now(TIMEZONE).isoformat(),
        "tasks": {
            "hu_de_sentences": [build_sentence_task(it, "hu_de") for it in hu_de_sentences],
            "de_hu_sentences": [build_sentence_task(it, "de_hu") for it in de_hu_sentences],
            "hu_de_vocab": [build_vocab_task(it, "hu_de") for it in hu_de_vocab],
            "de_hu_vocab": [build_vocab_task(it, "de_hu") for it in de_hu_vocab],
        },
    }

    all_used = hu_de_sentences + de_hu_sentences + hu_de_vocab + de_hu_vocab
    pool_lib.mark_used(usage_state, all_used, today)

    DAILY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DAILY_PATH.open("w", encoding="utf-8") as fh:
        json.dump(daily, fh, ensure_ascii=False, indent=2)

    pool_lib.save_usage_state(STATE_PATH, usage_state)

    print(f"Napi feladatsor legeneralva: {DAILY_PATH} ({today.isoformat()})")


if __name__ == "__main__":
    main()
