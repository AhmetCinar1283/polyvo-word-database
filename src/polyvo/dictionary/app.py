"""
`dictionary` app manifesti — bu katmanin CLI'ya kendini tanittigi tek dosya.

`core/cli/discovery.py` bu modulu bulur ve `APP`'i okur. Merkezde bir komut
listesi YOKTUR: bu dosyayi silmek app'i kaldirir, eklemek app'i kurar; hicbir
ust katman dosyasi duzenlenmez.
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.dictionary.build.commands import build_command, download_command

APP = App(
    name="dictionary",
    help="Sozluk veri hatti: kaynak indirme ve aday havuzu insasi",
    # Katman 1: yalnizca core'a bagimli. Bu beyan `tests/test_layering.py`
    # tarafindan gercek import grafigiyle karsilastirilir.
    depends=["core"],
    commands=[
        Command(
            name="download",
            help="Acik kaynak listelerini data/raw/ altina indirir",
            handler=download_command.cmd_download,
            add_args=download_command.add_download_args,
        ),
        Command(
            name="build",
            help="Aday havuzunu uretir (data/builds/<tag>/01_lexicon/)",
            handler=build_command.cmd_build,
            add_args=build_command.add_build_args,
        ),
    ],
)
