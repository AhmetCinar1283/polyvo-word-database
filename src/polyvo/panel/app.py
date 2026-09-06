"""
`panel` app manifesti — host'un kendisi de bir app'tir, ayricaligi yoktur.

`panel` alani BOSTUR: host kendi sayfasini getirmez, yalnizca baskalarininkini
tasir. `depends` her katmani sayar cunku sayfalar oradan gelir.
"""

from __future__ import annotations

from polyvo.core.cli.app import App, Command
from polyvo.panel.commands import serve_command

APP = App(
    name="panel",
    help="Panel host'u: APP.panel'i olan her modulun sayfasini servis eder (sifir LLM)",
    depends=["core", "dictionary", "curriculum", "modules", "delivery", "review"],
    commands=[
        Command(name="serve",
                help="Paneli baslatir (varsayilan http://127.0.0.1:8765/)",
                handler=serve_command.cmd_serve,
                add_args=serve_command.add_serve_args),
    ],
)
