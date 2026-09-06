"""
`polyvo delivery verify` — uretilmis sevkiyati bastan sona dogrular.

MIGRATION-PLAN §7'de bu komut `polyvo verify pipeline` diye anilir; app/komut
duzenine (`polyvo <app> <komut>`) uyum icin adi budur, isi aynidir.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.delivery import verify


def add_verify_args(parser: argparse.ArgumentParser) -> None:
    """`--tag`, `--l2`, `--l1` bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None, help="Hedef dil")
    parser.add_argument("--l1", default=None,
                        help="Ana dil; 'yok' verilirse i18n dosyasi beklenmez")


def cmd_verify(args: argparse.Namespace) -> int:
    """Kontrolleri kosar; bir tanesi bile duserse 1 doner."""
    tag = paths.resolve_tag(args.tag)
    l2 = args.l2 or config.default_l2()
    l1 = None if args.l1 == "yok" else (args.l1 or config.default_l1())

    results = verify.run_checks(tag, l2, l1)
    print(f"tag {tag}  l2 {l2}  l1 {l1 or '(yok)'}  —  {len(results)} kontrol\n")
    for result in results:
        print(result)

    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} kontrol gecti.")
    return 1 if failed else 0
