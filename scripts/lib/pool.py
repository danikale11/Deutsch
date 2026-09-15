"""A ket adatbazis (konyv_adatbazis.json, konyv_adatbazis_2.json) egyesitese
egy kozos pool-ba, ismetles-elkerules (cooldown) es sulyozott mintaveteles
gyenge temak fele.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DATA_DIR = REPO_ROOT / "docs" / "data"
DB_FILES = [
    REPO_ROOT / "konyv_adatbazis.json",
    REPO_ROOT / "konyv_adatbazis_2.json",
]
COOLDOWN_DAYS = 14


@dataclass
class Pool:
    vocab: list[dict[str, Any]] = field(default_factory=list)
    sentences: list[dict[str, Any]] = field(default_factory=list)
    chapter_titles: dict[str, str] = field(default_factory=dict)
    """kulcs: f"{source}:{chapter}" -> fejezet nyelvtani cime"""


def _chapter_key(source: str, chapter: int) -> str:
    return f"{source}:{chapter}"


def load_pool() -> Pool:
    pool = Pool()
    for db_path in DB_FILES:
        source = db_path.stem  # 'konyv_adatbazis' vagy 'konyv_adatbazis_2'
        with db_path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        for chapter_no, title in data["meta"]["chapters"].items():
            pool.chapter_titles[_chapter_key(source, int(chapter_no))] = title

        for item in data["vocabulary"]:
            enriched = dict(item)
            enriched["source"] = source
            enriched["kind"] = "vocab"
            enriched["chapter_title"] = pool.chapter_titles.get(
                _chapter_key(source, item["chapter"])
            )
            pool.vocab.append(enriched)

        for item in data["sentences"]:
            enriched = dict(item)
            enriched["source"] = source
            enriched["kind"] = "sentence"
            enriched["chapter_title"] = pool.chapter_titles.get(
                _chapter_key(source, item["chapter"])
            )
            pool.sentences.append(enriched)

    return pool


def load_usage_state(state_path: Path) -> dict[str, str]:
    if not state_path.exists():
        return {}
    with state_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_usage_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)


def filter_by_cooldown(
    items: list[dict[str, Any]],
    usage_state: dict[str, str],
    today: date,
    window_days: int = COOLDOWN_DAYS,
    min_pool_size: int = 5,
) -> list[dict[str, Any]]:
    """Kizarja azokat az elemeket, amiket az elmult `window_days` napban
    mar hasznaltunk. Ha ettol a szures utan a pool a `min_pool_size` ala
    csokkenne, a legregebben hasznaltak (vagy meg sosem hasznaltak)
    visszakerulnek, amig el nem eri a minimumot.
    """
    cutoff = today - timedelta(days=window_days)

    def last_used(item: dict[str, Any]) -> date | None:
        raw = usage_state.get(item["id"])
        if not raw:
            return None
        return date.fromisoformat(raw)

    fresh = [it for it in items if (lu := last_used(it)) is None or lu < cutoff]

    if len(fresh) >= min_pool_size:
        return fresh

    # Nincs eleg friss elem: a legregebben hasznaltak (soha hasznalt = legrégibb)
    # kerulnek vissza eloszor, amig el nem erjuk a minimumot.
    by_recency = sorted(
        items,
        key=lambda it: last_used(it) or date.min,
    )
    result = list(fresh)
    seen_ids = {it["id"] for it in result}
    for it in by_recency:
        if len(result) >= min_pool_size:
            break
        if it["id"] not in seen_ids:
            result.append(it)
            seen_ids.add(it["id"])
    return result


def _item_weight(item: dict[str, Any], weak_topics: dict[str, float] | None) -> float:
    base = 1.0
    if weak_topics:
        topic = item.get("topic")
        if topic and topic in weak_topics:
            # weak_topics erteke a hibaarany (0..1); minel gyengebb a tema,
            # annal nagyobb sulyt kap (max kb. 2.5x)
            base *= 1.0 + 1.5 * weak_topics[topic]
    return base


def weighted_sample_without_replacement(
    items: list[dict[str, Any]],
    k: int,
    weak_topics: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """Sulyozott mintavetel visszateves nelkul (Efraimidis-Spirakis A-ES
    algoritmus): minden elemhez kulcsot szamolunk `random() ** (1/weight)`
    alapon, majd a k legnagyobb kulcsu elemet valasztjuk. Csak a
    standard konyvtarat hasznalja, nincs kulso fuggoseg.
    """
    rng = rng or random.Random()
    if k >= len(items):
        return list(items)

    keyed = []
    for item in items:
        weight = max(_item_weight(item, weak_topics), 1e-6)
        u = rng.random()
        key = u ** (1.0 / weight)
        keyed.append((key, item))

    keyed.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in keyed[:k]]


def mark_used(usage_state: dict[str, str], items: list[dict[str, Any]], today: date) -> None:
    iso = today.isoformat()
    for item in items:
        usage_state[item["id"]] = iso
