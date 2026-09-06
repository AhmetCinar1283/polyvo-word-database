"""
`curriculum` app manifesti — bu katmanin CLI'ya kendini tanittigi tek dosya.

`core/cli/discovery.py` bu modulu bulur ve `APP`'i okur (bkz.
`dictionary/app.py`'nin ayni desendeki docstring'i).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.curriculum.commands import select_command

APP = App(
    name="curriculum",
    help="Evren secimi + kalici item_id/sense_id kimlik uzayi (sifir LLM)",
    # Katman 2a: core + dictionary'ye bagimli, LLM iceren `modules/`e degil.
    depends=["core", "dictionary"],
    commands=[
        Command(
            name="select",
            help="Evreni secer, kimlik tahsis eder, workspace/<tag>/<l2>/'ye izdusurur",
            handler=select_command.cmd_select,
            add_args=select_command.add_select_args,
        ),
    ],
)
