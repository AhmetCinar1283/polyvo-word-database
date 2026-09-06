"""
Yazma — adim 4 (tier suzme) ve adim 5 (`lexicon.sqlite`'a yazma).

Dosya HER KOSUDA sifirdan uretilir (once silinir, sonra yeniden yaratilir);
bu, iki kosunun birebir ayni sonucu vermesinin (determinizm) sarti. Satirlar
yazilmadan once SIRALANIR — bir `set`in dolasim sirasi Python surumleri
arasinda garanti degildir, sıralama olmadan determinizm testi kirilirdi.
"""

from __future__ import annotations

import os

from polyvo.core import sqlite as sq
from polyvo.dictionary import sources
from polyvo.dictionary.build import normalize, schema
from polyvo.dictionary.build.pool import Pool, Row


def filter_by_tier(pool: Pool, tier_max: int) -> list[Row]:
    """`--tier N` kapsamindaki adaylari doner. Kapsam disi satir bir kusur
    DEGILDIR; `unresolved`'a yazilmaz, sadece bu listeye girmez."""
    return [r for r in pool.rows.values() if r.tier is not None and r.tier <= tier_max]


def write_lexicon(db_path: str, pool: Pool, kept: list[Row]) -> None:
    """`kept` adaylarini + ait olduklari kanit/eleme satirlarini `db_path`'e yazar."""
    kept_heads = {r.headword for r in kept}

    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    con = sq.connect(db_path, ddl=schema.DDL)
    try:
        with con:
            con.executemany(
                "INSERT INTO candidates (headword, pos, tier, cefr, freq_rank,"
                " is_multiword, sources, pos_source) VALUES (?,?,?,?,?,?,?,?)",
                [(r.headword, r.pos, r.tier, r.cefr, r.freq_rank,
                  int(normalize.is_multiword(r.headword)),
                  ",".join(sorted(r.srcs)), r.pos_source)
                 for r in sorted(kept, key=lambda r: (r.headword, r.pos or ""))])
            con.executemany(
                "INSERT OR IGNORE INTO evidence (headword, pos, kind, payload,"
                " source) VALUES (?,?,?,?,?)",
                [(h, p, k, pay, s)
                 for (h, p, k, pay, s) in sorted(
                     pool.evidence, key=lambda e: (e[0], e[1] or "", e[2], e[3], e[4]))
                 if h in kept_heads])
            con.executemany(
                "INSERT OR IGNORE INTO unresolved (headword, raw_pos, source,"
                " reason) VALUES (?,?,?,?)",
                sorted(pool.unresolved, key=lambda u: (u[0], u[1] or "", u[2], u[3])))
            con.executemany(
                "INSERT INTO source_meta (source, title, license, attribution,"
                " shippable, tier, candidates_in, evidence_in)"
                " VALUES (?,?,?,?,?,?,?,?)",
                [(s.name, s.title, s.license, s.attribution, int(s.shippable),
                  s.tier, pool.counts.get(s.name, {}).get("candidates_in", 0),
                  pool.counts.get(s.name, {}).get("evidence_in", 0))
                 for s in (sources.get(n) for n in sorted(pool.counts))])
    finally:
        con.close()
