"""
`polyvo delivery materialize` — odenmis depodan sevkiyat dosyalarini uretir.

Bu dosya IS YAPMAZ: `materialize.run` cagirir ve sonucu raporlar. Kapi
ihlalinde ekrana ihlalleri basar, exit 1 doner ve "hicbir dosya yazilmadi"
der — bu cumle bir iddia degil, `materialize.run`'un yapisinin sonucudur.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.delivery import gate, materialize


def add_materialize_args(parser: argparse.ArgumentParser) -> None:
    """`--tag`, `--l2`, `--l1` bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--l1", default=None,
                        help="Ana dil; 'yok' verilirse i18n dosyasi uretilmez")


def cmd_materialize(args: argparse.Namespace) -> int:
    """Sevkiyati uretir; kapi ihlalinde sifir dosya yazip 1 doner."""
    tag = paths.resolve_tag(args.tag)
    l2 = args.l2 or config.default_l2()
    l1 = None if args.l1 == "yok" else (args.l1 or config.default_l1())

    try:
        result = materialize.run(tag, l2, l1)
    except gate.ShipGateError as exc:
        print(f"[delivery] SEVK KAPISI ihlal edildi, HICBIR DOSYA YAZILMADI:\n"
              f"  {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"[delivery] {exc}")
        return 1

    shipment = result.shipment
    print(f"tag {tag}  l2 {l2}  l1 {l1 or '(yok)'}  "
          f"sevk edilen {len(shipment.rows)} oge "
          f"(karti olmayan {shipment.skipped_missing}, "
          f"onaylanmamis {shipment.skipped_not_approved})")
    print(f"\n  {result.directory}")
    for name in result.filenames:
        info = result.meta["files"][name]
        print(f"    {name:<14} {info['bytes']:>9,} bayt  {info['sha256'][:16]}…")
    return 0
