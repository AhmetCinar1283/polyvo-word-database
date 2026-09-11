"""
`cloze` app manifesti — bu app'in CLI'ya ve panele kendini tanittigi tek
dosya (`core/cli/discovery.py` bulur).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.modules.cloze import public
from polyvo.modules.cloze.commands import (
    generate_command,
    rationale_command,
    rationale_translate_command,
    translate_command,
)
from polyvo.modules.cloze.panel import PAGE

APP = App(
    name="cloze",
    help="Onayli anlamlar icin coktan secmeli bosluk sorusu uretir (LLM harcar)",
    # Katman 3: kimligi curriculum'dan, seviyeyi dictionary'den, karti
    # lexicon_card'in ILAN EDILMIS okuma yuzeyinden alir.
    depends=["core", "dictionary", "curriculum"],
    commands=[
        Command(
            name="generate",
            help="Onayli her anlam icin 3 coktan secmeli bosluk sorusu uretir",
            handler=generate_command.cmd_generate,
            add_args=generate_command.add_generate_args,
            spends=True,
        ),
        Command(
            name="translate",
            help="Onaylanmis cloze CUMLELERINI bir ana dile cevirir (siklar cevrilmez)",
            handler=translate_command.cmd_translate,
            add_args=translate_command.add_translate_args,
            spends=True,
        ),
        Command(
            name="rationale",
            help="Onayli her cloze paketi icin ipucu + sik basina aciklama uretir",
            handler=rationale_command.cmd_rationale,
            add_args=rationale_command.add_rationale_args,
            spends=True,
        ),
        Command(
            name="rationale-translate",
            help="Onaylanmis ipucu/aciklamayi bir ana dile cevirir",
            handler=rationale_translate_command.cmd_rationale_translate,
            add_args=rationale_translate_command.add_rationale_translate_args,
            spends=True,
        ),
    ],
    panel=PAGE,
    sentences=public.SENTENCES,
)
