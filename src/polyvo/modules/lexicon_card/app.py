"""
`lexicon_card` app manifesti — bu app'in CLI'ya ve panele kendini tanittigi
tek dosya (`core/cli/discovery.py` bulur).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.modules.lexicon_card.commands import (
    cards_command,
    note_command,
    translate_command,
)
from polyvo.modules.lexicon_card.panel import PAGE

APP = App(
    name="lexicon-card",
    help="EN sozluk karti, ornek ve ana dil karsiligi uretir (LLM harcar)",
    # Katman 3: kimligi curriculum'dan, kaniti dictionary'den alir.
    depends=["core", "dictionary", "curriculum"],
    commands=[
        Command(
            name="cards",
            help="Evrendeki kelimeler icin INGILIZCE kart uretir; dile bagli degil — ana dil karsiligi ayri kosudur: translate --l1 <kod>",
            handler=cards_command.cmd_cards,
            add_args=cards_command.add_cards_args,
            spends=True,
        ),
        Command(
            name="note",
            help="Onayli kartin ustune KOSULLU kullanim notu uretir (dile bagli degil)",
            handler=note_command.cmd_note,
            add_args=note_command.add_note_args,
            spends=True,
        ),
        Command(
            name="translate",
            help="Onayli kartin L1 karsiligini ve tanim+not+ornek cevirisini TEK cagrida uretir (kart tekrar odenmez)",
            handler=translate_command.cmd_translate,
            add_args=translate_command.add_translate_args,
            spends=True,
        ),
    ],
    panel=PAGE,
)
