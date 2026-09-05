"""
Bir "app"in sozlesmesi — Django'nun AppConfig'ine karsilik gelen sey.

Bir app KENDINI tanitir: hangi komutlari var, hangi panel sayfasini getiriyor,
kime bagimli. Merkezde app listesi TUTULMAZ; `discovery.py` paketleri gezip
`APP` degiskenini bulur. Yeni bir is eklemek = yeni bir klasor; hicbir mevcut
dosya duzenlenmez. (Eski repoda bunun bedeli olculebilirdi: yeni bir uretim
komutu `manage.py`'nin 437 satirini, `panel/server.py`'nin sabit import
blogunu, `runner.py`'yi ve `review.py`'yi ayni anda degistirmeyi gerektiriyor,
`reading` modulunun paneli de tam bu yuzden hic yazilmamisti.)

BAGIMLILIK YONU (demir kural): app'ler yukari dogru import edemez. `depends`
alani bu yuzden bir metin listesidir, import degil — `tests/test_layering.py`
hem beyani hem gercek import grafigini kontrol eder.
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
    name: str
    help: str = ""
    commands: list[Command] = field(default_factory=list)
    panel: PanelPage | None = None
    jobs: list = field(default_factory=list)
    depends: list[str] = field(default_factory=list)

    def command(self, name: str) -> Command | None:
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None
