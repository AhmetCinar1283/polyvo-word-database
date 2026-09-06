"""
Bir "app"in sozlesmesi. App KENDINI tanitir (komutlar, panel, bagimlilik);
merkezde app listesi TUTULMAZ — `discovery.py` paketleri gezip `APP`'i bulur.

`depends` bir metin listesidir, import degil — `tests/test_layering.py` hem
beyani hem gercek import grafigini kontrol eder (demir kural: yukari import yok).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import argparse


@dataclass
class Command:
    """Tek bir CLI alt-komutu: `polyvo <app> <name>`."""
    name: str
    help: str
    handler: Callable[[argparse.Namespace], int]
    add_args: Callable[[argparse.ArgumentParser], None] | None = None
    #: Bu komut LLM cagrisi yapabilir mi (rapor ve `--dry-run` beklentisi icin).
    spends: bool = False


@dataclass
class PanelPage:
    """App'in panel host'a getirdigi sayfa. `router`, panel katmani
    yazilincaya kadar `None` kalabilir — app'in geri kalani ondan bagimsiz."""
    prefix: str
    title: str
    router: object | None = None
    static_dir: str | None = None
    order: int = 100


@dataclass
class App:
    """Bir app'in kendini tanittigi manifest — `APP` degiskeni bu tipte olur."""
    name: str
    help: str = ""
    commands: list[Command] = field(default_factory=list)
    panel: PanelPage | None = None
    jobs: list = field(default_factory=list)
    depends: list[str] = field(default_factory=list)

    def command(self, name: str) -> Command | None:
        """Adiyla bir komut bulur; yoksa `None`."""
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None
