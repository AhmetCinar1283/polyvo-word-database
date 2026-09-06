"""
`lexicon_card` app manifesti — bu app'in CLI'ya ve panele kendini tanittigi
tek dosya (`core/cli/discovery.py` bulur).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.modules.lexicon_card.commands import cards_command
from polyvo.modules.lexicon_card.panel import PAGE

APP = App(
    name="lexicon-card",
    help="EN sozluk karti + L1 gloss + ornek uretir (LLM harcar)",
    # Katman 3: kimligi curriculum'dan, kaniti dictionary'den alir.
    depends=["core", "dictionary", "curriculum"],
    commands=[
        Command(
            name="cards",
            help="Evrendeki kelimeler icin kart uretir (plan + onay + yazma kapisi)",
            handler=cards_command.cmd_cards,
            add_args=cards_command.add_cards_args,
            spends=True,
        ),
    ],
    panel=PAGE,
)
