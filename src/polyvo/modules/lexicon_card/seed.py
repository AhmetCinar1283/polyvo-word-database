"""
Sozluk tohumu — `builds/<tag>/01_lexicon/lexicon.sqlite`'taki `evidence`
satirlarini birimlere baglar. Iki AYRI amac, karistirilmamali:

  * `context`  -> yalnizca PROMPT'a girer. Kaynagi `shippable=False` olabilir
    (legacy tanimlari gibi); depoya ve `dist/`e ASLA yazilmaz.
  * `ipa`      -> DEPOYA yazilabilir, cunku yalnizca `shippable=True`
    kaynaklardan (ipa_dict, MIT) alinir ve IPA bir OLGUDUR.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field

from polyvo.dictionary import sources

#: Prompt'a en cok kac kanit parcasi girer (token maliyeti sinirli kalsin).
MAX_CONTEXT_PER_KIND = 3

#: Prompt'a baglam olarak giren kanit turleri.
CONTEXT_KINDS = ("definition", "example", "synonym")


@dataclass
class Seed:
    """Bir kelimenin tohumu: prompt baglami + sevk edilebilir IPA."""
    ipa: str | None = None
    context: dict[str, list[str]] = field(default_factory=dict)


def _shippable_sources() -> set[str]:
    """`dist/`e metni yazilabilen kaynaklarin adlari."""
    return {s.name for s in sources.SOURCES.values() if s.shippable}


def load_seeds(db_path: str, headwords: list[str]) -> dict[str, Seed]:
    """Verilen kelimeler icin `headword -> Seed`. Build dosyasi yoksa bos doner
    — tohum bir KOLAYLIKTIR, yokluğu kosuyu durdurmaz."""
    if not headwords or not os.path.exists(db_path):
        return {}

    shippable = _shippable_sources()
    seeds: dict[str, Seed] = {}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for chunk in _chunks(headwords, 400):
            marks = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"SELECT headword, kind, payload, source FROM evidence"
                f" WHERE headword IN ({marks})", chunk).fetchall()
            for headword, kind, payload, source in rows:
                seed = seeds.setdefault(headword, Seed())
                if kind == "ipa":
                    # IPA yalnizca sevk edilebilir kaynaktan; ilk gelen kalir.
                    if seed.ipa is None and source in shippable:
                        seed.ipa = payload
                elif kind in CONTEXT_KINDS:
                    bucket = seed.context.setdefault(kind, [])
                    if len(bucket) < MAX_CONTEXT_PER_KIND:
                        bucket.append(payload)
    finally:
        conn.close()
    return seeds


def _chunks(values: list[str], size: int):
    """SQLite'in degisken sinirina takilmamak icin listeyi parcalara boler."""
    for start in range(0, len(values), size):
        yield values[start:start + size]


def attach(units, seeds: dict[str, Seed]) -> None:
    """Her birimin `data["seed"]` alanina kendi tohumunu yerlestirir."""
    for unit in units:
        unit.data["seed"] = seeds.get(unit.data["headword"], Seed())
