"""
`grammar` app manifesti — bu app'in CLI'ya ve panele kendini tanittigi tek
dosya (`core/cli/discovery.py` bulur).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.modules.grammar.commands import (
    analyze_command,
    catalog_translate_command,
    translate_command,
)
from polyvo.modules.grammar.panel import PAGE

APP = App(
    name="grammar",
    help="Onayli cumlelerdeki goze carpan gramer kurallarini cikarir (LLM harcar)",
    # Katman 3: cumleleri BASKA app'lerin ilan ettigi APP.sentences seam'inden
    # okur — hicbir kardes modules/* paketini import ETMEZ.
    depends=["core"],
    commands=[
        Command(
            name="analyze",
            help="Her cumle grubu icin en cok uc kurallik grammar paketi uretir",
            handler=analyze_command.cmd_analyze,
            add_args=analyze_command.add_analyze_args,
            spends=True,
        ),
        Command(
            name="translate",
            help="Onayli grammar paketinin cumleye ozel notlarini bir L1'e cevirir",
            handler=translate_command.cmd_translate,
            add_args=translate_command.add_translate_args,
            spends=True,
        ),
        Command(
            name="catalog-translate",
            help="Katalogdaki her kuralin isim + kisa aciklamasini bir L1'e cevirir",
            handler=catalog_translate_command.cmd_catalog_translate,
            add_args=catalog_translate_command.add_catalog_translate_args,
            spends=True,
        ),
    ],
    panel=PAGE,
)
