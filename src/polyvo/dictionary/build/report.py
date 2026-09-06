"""
Rapor — bir build kosusunun olculebilir ozeti.

`BuildReport` veridir, `summarize()` onu `Pool` + yazilan satirlardan uretir,
`print_report()` onu terminale basar. Uc is ayri tutulur ki rapor formati
(nasil goruntulendigi) build mantigindan bagimsiz degisebilsin.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from polyvo.dictionary.build import normalize
from polyvo.dictionary.build.pool import Pool, Row


@dataclass
class BuildReport:
    """Bir `polyvo dictionary build` kosusunun sonuc sayilari."""
    rows: int = 0
    evidence: int = 0
    unresolved: int = 0
    by_tier: Counter = field(default_factory=Counter)
    by_pos: Counter = field(default_factory=Counter)
    by_cefr: Counter = field(default_factory=Counter)
    by_reason: Counter = field(default_factory=Counter)
    per_source: dict[str, dict[str, int]] = field(default_factory=dict)
    pos_recovered: int = 0
    pos_missing: int = 0
    evidence_out_of_universe: int = 0
    multiword: int = 0


def summarize(pool: Pool, kept: list[Row], *, written_rows: int, written_evidence: int,
             written_unresolved: int, pos_recovered: int, pos_missing: int) -> BuildReport:
    """`pool` ve yazilan `kept` satirlardan bir `BuildReport` uretir."""
    report = BuildReport(
        rows=written_rows, evidence=written_evidence, unresolved=written_unresolved,
        pos_recovered=pos_recovered, pos_missing=pos_missing,
        evidence_out_of_universe=pool.evidence_out_of_universe,
        per_source=pool.counts,
    )
    for row in kept:
        report.by_tier[row.tier] += 1
        report.by_pos[row.pos or "(yok)"] += 1
        report.by_cefr[row.cefr or "(yok)"] += 1
        report.multiword += int(normalize.is_multiword(row.headword))
    for _h, _rp, _s, reason in pool.unresolved:
        report.by_reason[reason] += 1
    return report


def print_report(r: BuildReport) -> None:
    """Raporu okunur satirlar halinde terminale basar."""
    print(f"\naday satiri     {r.rows:>7}   (cok kelimeli {r.multiword})")
    print(f"kanit satiri    {r.evidence:>7}   (evren disi atlandi "
          f"{r.evidence_out_of_universe})")
    print(f"cozulemeyen     {r.unresolved:>7}")

    print("\ntier      " + "  ".join(f"{k}:{v}" for k, v in sorted(r.by_tier.items())))
    print("pos       " + "  ".join(f"{k}:{v}" for k, v in r.by_pos.most_common()))
    print("cefr      " + "  ".join(f"{k}:{v}" for k, v in sorted(r.by_cefr.items())))
    print(f"\nPOS kanittan cozuldu {r.pos_recovered}   POS'suz kalan {r.pos_missing}")
    if r.by_reason:
        print("eleme sebepleri  "
              + "  ".join(f"{k}:{v}" for k, v in r.by_reason.most_common()))
