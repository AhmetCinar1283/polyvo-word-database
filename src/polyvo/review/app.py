"""
`review` app manifesti — insan duzeltme yolunun CLI'ya tanitildigi dosya.
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.review.commands import export_command, import_command, restore_command

APP = App(
    name="review",
    help="Insan duzeltme yolu: export -> duzelt -> import (tier 0, sifir LLM)",
    depends=["core", "curriculum", "modules"],
    commands=[
        Command(name="export",
                help="Duzeltilecek satirlari JSONL olarak cikarir",
                handler=export_command.cmd_export,
                add_args=export_command.add_export_args),
        Command(name="import",
                help="Duzeltilmis dosyayi yazar (sorunlu satir varsa sifir yazma)",
                handler=import_command.cmd_import,
                add_args=import_command.add_import_args),
        Command(name="restore",
                help="data/human/ yedegini depoya geri oynatir",
                handler=restore_command.cmd_restore,
                add_args=restore_command.add_restore_args),
    ],
)
