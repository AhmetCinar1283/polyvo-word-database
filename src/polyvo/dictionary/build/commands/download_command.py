"""`polyvo dictionary download` — kaynaklari `data/raw/`'a indirir/kopyalar."""

from __future__ import annotations

import argparse
import os

from polyvo.core import paths
from polyvo.dictionary.build import download


def add_download_args(parser: argparse.ArgumentParser) -> None:
    """`--force`: mevcut dosyalari yeniden indir."""
    parser.add_argument("--force", action="store_true",
                        help="Mevcut dosyalari yeniden indir")


def cmd_download(args: argparse.Namespace) -> int:
    """Her kaynagi indirir/kopyalar ve durumunu terminale basar."""
    paths.ensure_dirs()
    results = download.download_all(force=args.force)
    for name, status, path in results:
        size = ""
        if path and os.path.isfile(path):
            size = f"  {os.path.getsize(path) / 1_048_576:.1f} MB"
        print(f"  {name:<12} {status:<12}{size}")
    missing = [n for n, s, _ in results if s in ("url_yok", "kaynak_yok")]
    if missing:
        print(f"\nElle yerlestirilmesi gerekenler: {', '.join(missing)}")
    print(f"\n{paths.raw_dir()}")
    return 0
