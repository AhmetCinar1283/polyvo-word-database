"""
`delivery` app manifesti — sevkiyat katmaninin CLI'ya kendini tanittigi dosya.

`depends` LLM ureten katmani da icerir: sevkiyat `modules/`in yazdigi odenmis
depodan okur (asagi dogru, demir kurala uygun).
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.delivery.commands import materialize_command, verify_command

APP = App(
    name="delivery",
    help="Odenmis depodan sevkiyat uretir: core.db · <l2>.db · i18n_<l1>.db (sifir LLM)",
    depends=["core", "dictionary", "curriculum", "modules"],
    commands=[
        Command(
            name="materialize",
            help="Sevkiyat dosyalarini uretir (kapi ONCE calisir, ihlalde sifir dosya)",
            handler=materialize_command.cmd_materialize,
            add_args=materialize_command.add_materialize_args,
        ),
        Command(
            name="verify",
            help="Uretilmis sevkiyati uctan uca dogrular",
            handler=verify_command.cmd_verify,
            add_args=verify_command.add_verify_args,
        ),
    ],
)
