"""
`polyvo review restore` — `data/human/` yedegini depoya geri oynatir.

Yedegin varlik sebebi budur: kimlik uzayi yeniden kurulsa da insan emegi
geri gelir. Ayni kapidan gecer, tier/source yine SABITTIR — geri oynatma
ayricalikli bir yol degildir.
"""

from __future__ import annotations

import argparse

from polyvo.core import config
from polyvo.review import apply as apply_mod
from polyvo.review import backup


def add_restore_args(parser: argparse.ArgumentParser) -> None:
    """`--l1` bayragi (satirinda `l1` olmayan kayitlar icin)."""
    parser.add_argument("--l1", default=None,
                        help="Satirinda `l1` yazmayan kayitlar icin ana dil")


def cmd_restore(args: argparse.Namespace) -> int:
    """Yedegi okur ve ice aktarma yoluyla uygular."""
    corrections, problems = backup.read()
    if problems:
        print(f"[review] Yedek {len(problems)} sorunlu satir iceriyor, "
              f"HICBIR SATIR YAZILMADI:")
        for problem in problems[:20]:
            print(f"  {problem}")
        return 1
    if not corrections:
        print(f"[review] Yedek bos ya da yok: {backup.backup_path()}")
        return 0

    try:
        # Yedek depodan BUYUK olabilir (kimlik yeniden kuruldu): eksik
        # anahtarlar hata degil, atlanir. Yedege TEKRAR yazilmaz.
        result = apply_mod.apply(corrections, l1=args.l1 or config.default_l1(),
                                 skip_unknown=True, write_backup=False)
    except apply_mod.ReviewError as exc:
        print(f"[review] HICBIR SATIR YAZILMADI:\n  {exc}")
        return 1

    print(f"{result.applied} duzeltme geri yuklendi "
          f"({result.skipped_unknown} anahtar depoda yok, atlandi)")
    return 0
