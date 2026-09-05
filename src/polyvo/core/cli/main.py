"""
`polyvo` giris noktasi.

Eski `manage.py`'den iki fark, ikisi de bilincli:

  * ALT SUREC YOK. Eski dispatcher her komut icin yeni bir Python baslatiyor,
    cikis kodunu elle geri tasiyordu. Burada komut bir fonksiyondur; cikis kodu
    dogal olarak dogru, hata izi tektir, import maliyeti bir kez odenir.
  * SABIT KOMUT LISTESI YOK. Alt-komutlar `discovery.find_apps()`'ten gelir.

Kullanim:  polyvo <app> <komut> [...]      orn. polyvo dict build --limit 500
           polyvo apps                     yuklu app'ler ve komutlari
           polyvo where                    cozulen yollar ve aktif tag
"""

from __future__ import annotations

import argparse
import sys

from polyvo.core import config, paths
from polyvo.core.cli import discovery


def _cmd_apps(_args) -> int:
    apps = discovery.find_apps()
    if not apps:
        print("Henuz hicbir app yuklu degil (katmanlar tasindikca burada gorunur).")
        return 0
    for app in apps:
        panel = f"  [panel {app.panel.prefix}]" if app.panel else ""
        print(f"{app.name:<16} {app.help}{panel}")
        for cmd in app.commands:
            spend = " $" if cmd.spends else ""
            print(f"    {app.name} {cmd.name:<20}{spend} {cmd.help}")
    return 0


def _cmd_where(args) -> int:
    print(f"kok            {config.project_root()}")
    print(f"konfig         {config.config_path()}")
    print(f"veri koku      {paths.data_root()}")
    for name, fn in (("raw", paths.raw_dir), ("cache", paths.cache_dir),
                     ("stores", paths.stores_dir), ("human", paths.human_dir)):
        print(f"  {name:<12} {fn()}")
    tags = paths.list_tags()
    print(f"tag adaylari   {', '.join(tags) if tags else '(yok)'}")
    try:
        tag = paths.resolve_tag(args.tag)
    except SystemExit as exc:
        print(f"aktif tag      COZULEMEDI\n{exc}")
        return 0
    print(f"aktif tag      {tag}")
    print(f"  builds       {paths.build_dir(tag, '<asama>')}")
    print(f"  workspace    {paths.workspace_dir(tag)}")
    print(f"  dist         {paths.dist_dir(tag)}")
    return 0


def _cmd_init(_args) -> int:
    paths.ensure_dirs()
    print(f"Veri dizinleri hazir: {paths.data_root()}")
    return 0


BUILTINS = [
    ("apps", "Yuklu app'leri ve komutlarini listeler", _cmd_apps, False),
    ("where", "Cozulen yollari ve aktif tag'i yazar", _cmd_where, True),
    ("init", "data/ altindaki global dizinleri olusturur", _cmd_init, False),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polyvo", description="Polyvo kelime veritabani hatti")
    subs = parser.add_subparsers(dest="_app", metavar="<app>")

    for name, help_text, handler, wants_tag in BUILTINS:
        sub = subs.add_parser(name, help=help_text)
        if wants_tag:
            sub.add_argument("--tag", "--data-title", dest="tag", default=None)
        sub.set_defaults(_handler=handler)

    for app in discovery.find_apps():
        app_parser = subs.add_parser(app.name, help=app.help)
        cmd_subs = app_parser.add_subparsers(dest="_command", metavar="<komut>")
        for cmd in app.commands:
            cmd_parser = cmd_subs.add_parser(cmd.name, help=cmd.help)
            if cmd.add_args:
                cmd.add_args(cmd_parser)
            cmd_parser.set_defaults(_handler=cmd.handler)
        app_parser.set_defaults(_handler=None, _parser=app_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:
        # App verildi ama komut verilmedi: o app'in yardimini goster.
        own = getattr(args, "_parser", None) or parser
        own.print_help()
        return 1
    return int(handler(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
