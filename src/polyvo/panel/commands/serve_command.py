"""
`polyvo panel serve` — panel host'unu baslatir.

Bu dosya IS YAPMAZ: bayraklari `server.serve`e gecirir.
"""

from __future__ import annotations

import argparse

from polyvo.panel import pages as pages_mod
from polyvo.panel import server


def add_serve_args(parser: argparse.ArgumentParser) -> None:
    """`--host`, `--port`, `--list` bayraklari."""
    parser.add_argument("--host", default=server.DEFAULT_HOST,
                        help=f"Dinlenecek adres (varsayilan {server.DEFAULT_HOST}; "
                             f"aga acmak ACIK bir karardir)")
    parser.add_argument("--port", type=int, default=server.DEFAULT_PORT,
                        help=f"Port (varsayilan {server.DEFAULT_PORT})")
    parser.add_argument("--list", action="store_true",
                        help="Sunucuyu acmadan yalnizca sayfalari listeler")


def cmd_serve(args: argparse.Namespace) -> int:
    """Sayfalari listeler ya da sunucuyu calistirir."""
    if args.list:
        pages = pages_mod.mounted_pages()
        if not pages:
            print("Hicbir app panel sayfasi getirmiyor.")
            return 0
        for page in pages:
            state = "bagli" if page.connected else "router yok"
            print(f"{page.prefix:<18} {page.title:<24} [{page.app_name}]  {state}")
        return 0
    return server.serve(args.host, args.port)
