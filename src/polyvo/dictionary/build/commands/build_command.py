"""
`polyvo dictionary build` — aday havuzunu uretir ve `_stage_meta.json` yazar.

Bu dosya IS YAPMAZ: argumani cozer, `merge.build()`'i cagirir, sonucu basar
ve asama meta'sina yazar. Birlestirme mantiginin kendisi `build/merge.py` ve
onun cagirdigi adim dosyalarindadir.
"""

from __future__ import annotations

import argparse

from polyvo.core import paths
from polyvo.dictionary import sources
from polyvo.dictionary.build import merge, stages
from polyvo.dictionary.build.ingestors import find_ingestors
from polyvo.dictionary.build.report import BuildReport, print_report

#: Evren merdiveninin en ust basamagi (docs/SOURCES.md §2.1).
MAX_TIER = 3


def add_build_args(parser: argparse.ArgumentParser) -> None:
    """`--tag` (veri basligi) ve `--tier` (evren merdiveninde son basamak)."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--tier", type=int, default=MAX_TIER,
                        help=f"Evren merdiveninde son basamak (1..{MAX_TIER})")


def cmd_build(args: argparse.Namespace) -> int:
    """`data/builds/<tag>/01_lexicon/lexicon.sqlite`'i uretir ve raporlar."""
    if not 1 <= args.tier <= MAX_TIER:
        raise SystemExit(f"[polyvo] --tier 1..{MAX_TIER} arasinda olmali: {args.tier}")
    tag = paths.resolve_tag(args.tag)

    ingestors = find_ingestors()
    if not any(ing.available() for ing in ingestors):
        raise SystemExit(
            "[polyvo] data/raw/ altinda hicbir kaynak yok. "
            "Once: polyvo dictionary download")

    print(f"tag {tag}  |  tier <= {args.tier}")
    for ing in ingestors:
        src = sources.get(ing.source_name)
        mark = "+" if ing.available() else "-"
        print(f"  {mark} {src.name:<12} tier {str(src.tier or '-'):<3} {src.license}")

    db_path = stages.lexicon_db_path(tag)
    report = merge.build(db_path, tier_max=args.tier, ingestors=ingestors)
    print_report(report)

    meta_path = stages.write_stage_meta(tag, stages.LEXICON, _stage_meta_payload(
        tag=tag, tier_max=args.tier, report=report))
    print(f"\n  {db_path}\n  {meta_path}")
    return 0


def _stage_meta_payload(*, tag: str, tier_max: int, report: BuildReport) -> dict:
    """`_stage_meta.json` icerigi. Lisans bilgisi ciktiyla BIRLIKTE seyahat
    eder: Adim 6'daki sevk kapisi bunu okur, kaynak koda bakmaz."""
    return {
        "tier_max": tier_max,
        "database": stages.LEXICON_DB,
        "row_counts": stages.lexicon_row_counts(tag),
        "counts": {
            "candidates": report.rows,
            "evidence": report.evidence,
            "unresolved": report.unresolved,
            "multiword": report.multiword,
            "pos_recovered": report.pos_recovered,
            "pos_missing": report.pos_missing,
        },
        "distributions": {
            "tier": {str(k): v for k, v in sorted(report.by_tier.items())},
            "pos": dict(report.by_pos.most_common()),
            "cefr": dict(sorted(report.by_cefr.items())),
        },
        "sources": [
            {"name": s.name, "title": s.title, "license": s.license,
             "attribution": s.attribution, "shippable": s.shippable,
             "tier": s.tier,
             "candidates_in": report.per_source.get(s.name, {}).get("candidates_in", 0),
             "evidence_in": report.per_source.get(s.name, {}).get("evidence_in", 0)}
            for s in (sources.get(n) for n in sorted(report.per_source))
        ],
    }
