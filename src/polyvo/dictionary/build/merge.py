"""
Orkestrasyon — `build()` tek basina IS YAPMAZ, adimlari SIRAYLA cagirir.

Sira onemlidir, her adim bir oncekinin ciktisina dayanir:

  1. `collect.collect_candidates`  evreni kurar
  2. `collect.collect_evidence`    evrenin uzerine kanit ekler
  3. `resolve_pos.resolve_pos`     POS'suz satirlari cozer (K7)
  4. `write_lexicon.filter_by_tier` `--tier N` kapsamini secer
  5. `write_lexicon.write_lexicon`  `lexicon.sqlite`'a yazar
  6. `report.summarize`            olculebilir bir ozet uretir

Her adimin kendi dosyasi ve tek sorumlulugu var; bu dosya yalnizca sirayi
ve aralarindaki veri akisini gosterir.
"""

from __future__ import annotations

from typing import Iterable

from polyvo.core import sqlite as sq
from polyvo.dictionary.build import collect, resolve_pos, write_lexicon
from polyvo.dictionary.build.ingestors import Ingestor, find_ingestors
from polyvo.dictionary.build.pool import Pool
from polyvo.dictionary.build.report import BuildReport, summarize

__all__ = ["BuildReport", "build"]


def build(db_path: str, *, tier_max: int,
          ingestors: Iterable[Ingestor] | None = None) -> BuildReport:
    """`lexicon.sqlite`'i SIFIRDAN uretir ve raporu doner."""
    ings = list(ingestors) if ingestors is not None else find_ingestors()
    pool = Pool()

    collect.collect_candidates(pool, ings)
    collect.collect_evidence(pool, ings)
    recovered, missing = resolve_pos.resolve_pos(pool)

    kept = write_lexicon.filter_by_tier(pool, tier_max)
    write_lexicon.write_lexicon(db_path, pool, kept)

    counts = sq.row_counts(db_path) or {}
    return summarize(
        pool, kept,
        written_rows=counts.get("candidates", 0),
        written_evidence=counts.get("evidence", 0),
        written_unresolved=counts.get("unresolved", 0),
        pos_recovered=recovered, pos_missing=missing,
    )
