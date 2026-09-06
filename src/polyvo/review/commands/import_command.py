"""
`polyvo review import` — duzeltilmis dosyayi depoya yazar (tier 0, human).

Sorunlu tek satir varsa exit 1 doner ve HICBIR SATIR yazilmaz; bu bir uyari
degil, `apply.apply`'in yapisinin sonucudur.
"""

from __future__ import annotations

import argparse
import os

from polyvo.core import config
from polyvo.review import apply as apply_mod
from polyvo.review import record


def add_import_args(parser: argparse.ArgumentParser) -> None:
    """`--file`, `--l1`, `--skip-unknown`, `--no-backup` bayraklari."""
    parser.add_argument("--file", required=True, help="Duzeltilmis JSONL dosyasi")
    parser.add_argument("--l1", default=None,
                        help="`gloss_l1`in dili (satirda `l1` varsa o kazanir)")
    parser.add_argument("--skip-unknown", action="store_true",
                        help="Depoda karsiligi olmayan anahtarlari atla (kimlik URETILMEZ)")
    parser.add_argument("--no-backup", action="store_true",
                        help="data/human/ yedegine yazma (onerilmez)")


def cmd_import(args: argparse.Namespace) -> int:
    """Dosyayi okur, dogrular ve tek transaction'da yazar."""
    if not os.path.exists(args.file):
        print(f"[review] Dosya yok: {args.file}")
        return 1

    corrections, problems = record.parse_file(args.file)
    if problems:
        print(f"[review] Dosya {len(problems)} sorunlu satir iceriyor, "
              f"HICBIR SATIR YAZILMADI:")
        for problem in problems[:20]:
            print(f"  {problem}")
        return 1
    if not corrections:
        print("[review] Dosyada duzeltme yok.")
        return 0

    try:
        result = apply_mod.apply(
            corrections, l1=args.l1 or config.default_l1(),
            skip_unknown=args.skip_unknown, write_backup=not args.no_backup)
    except apply_mod.ReviewError as exc:
        print(f"[review] HICBIR SATIR YAZILMADI:\n  {exc}")
        return 1

    print(f"{result.applied} duzeltme yazildi (tier 0, source 'human')")
    if result.skipped_unknown:
        print(f"  depoda karsiligi olmayan {result.skipped_unknown} anahtar atlandi")
    if result.ignored_fields:
        print(f"  {result.ignored_fields} alan yok sayildi (tier/source dosyadan OKUNMAZ)")
    if result.still_unapproved:
        print(f"  UYARI: {len(result.still_unapproved)} kart hala 'approved' degil, "
              f"sevkiyata girmez: {', '.join(result.still_unapproved[:5])}")
    if result.backup_path:
        print(f"  yedek: {result.backup_path}")
    return 0
