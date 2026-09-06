"""
`polyvo review export` — duzeltilecek satirlari JSONL dosyasina cikarir.

Bu dosya IS YAPMAZ: `export.rows`/`export.write` cagirir ve insana dosyayi
nasil duzeltecegini soyler.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.review import export, record


def add_export_args(parser: argparse.ArgumentParser) -> None:
    """`--tag`, `--l2`, `--l1`, `--status`, `--limit`, `--out` bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yalnizca varsayilan cikti yolu icin)")
    parser.add_argument("--l2", default=None, help="Hedef dil (varsayilan: konfig)")
    parser.add_argument("--l1", default=None,
                        help="Ana dil; 'yok' verilirse L1 gloss'u cikarilmaz")
    parser.add_argument("--status", default=export.STATUS_ALL,
                        help="'approved', 'rejected' ya da 'all' (varsayilan)")
    parser.add_argument("--limit", type=int, default=None, help="Ilk N satir")
    parser.add_argument("--out", default=None,
                        help="Cikti dosyasi (varsayilan: workspace altinda)")


def cmd_export(args: argparse.Namespace) -> int:
    """Satirlari cikarir, dosya yolunu ve duzeltme talimatini yazar."""
    l2 = args.l2 or config.default_l2()
    l1 = None if args.l1 == "yok" else (args.l1 or config.default_l1())
    tag = paths.resolve_tag(args.tag)
    out = args.out or export.default_path(paths.workspace_dir(tag, l2))

    rows = export.rows(l1, status=args.status, limit=args.limit)
    if not rows:
        print(f"[review] '{args.status}' durumunda cikarilacak satir yok.")
        return 0

    path = export.write(rows, out)
    print(f"{len(rows)} satir cikarildi -> {path}")
    print("  Duzeltmek icin: satirdaki alani degistirin; DOKUNMAK ISTEMEDIGINIZ"
          " alani SILIN (bulunmayan alan degismez).")
    print(f"  Duzeltilebilir alanlar: {', '.join(record.EDITABLE_FIELDS)}")
    print(f"  Geri yazmak icin: polyvo review import --file {path}")
    return 0
