"""
Bir "app"in sozlesmesi. App KENDINI tanitir (komutlar, panel, bagimlilik);
merkezde app listesi TUTULMAZ — `discovery.py` paketleri gezip `APP`'i bulur.

`depends` bir metin listesidir, import degil — `tests/test_layering.py` hem
beyani hem gercek import grafigini kontrol eder (demir kural: yukari import yok).

`SentenceSource` (İş 6, `grammar` için) — bir app'in ürettiği cümleleri
KATKI SEAM'i olarak sunduğu sözleşme. Tüketen app (`grammar`) bunu
`discovery.find_apps()` ile toplar; hiçbir kardeş app'i import ETMEZ. Böylece
beşinci bir soru tipi eklendiğinde tüketen tarafta tek satır değişmez.
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


@dataclass(frozen=True)
class SentenceRef:
    """Analiz edilecek TEK cümle. `focus_word`/`focus_pos` isteğe bağlıdır;
    kural SEÇİMİNİ yönlendirmez, yalnızca prompt'a bağlam olarak girer."""
    ref: str
    text: str
    cefr: str | None = None
    focus_word: str | None = None
    focus_pos: str | None = None


@dataclass(frozen=True)
class SentenceGroup:
    """Tek çağrıda birlikte analiz edilecek cümle kümesi (örn. bir anlamın
    üç cloze cümlesi). `group_key` depo anahtarıdır, kalıcıdır."""
    group_key: str
    sentences: tuple[SentenceRef, ...]


@dataclass(frozen=True)
class SentenceSource:
    """Bir app'in cümlelerini KATKI SEAM'i üzerinden sunduğu ilan.

    `owner` app adıdır ve KİMLİĞİN PARÇASIDIR, sonradan değişmez — tüketen
    taraf `f"{owner}|{group_key}"` biçiminde birim anahtarı üretir, böylece
    iki app'in aynı `group_key`i aynı tabloda çakışmaz.
    `loader(tag, l2) -> list[SentenceGroup]` yalnızca ONAYLI/sevk edilebilir
    içeriği döner — reddedilmiş ya da hiç üretilmemiş içerik hiç görünmez."""
    owner: str
    loader: Callable[[str, str], list["SentenceGroup"]]


@dataclass
class App:
    """Bir app'in kendini tanittigi manifest — `APP` degiskeni bu tipte olur."""
    name: str
    help: str = ""
    commands: list[Command] = field(default_factory=list)
    panel: PanelPage | None = None
    jobs: list = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    #: Bu app'in başka app'lere sunduğu cümle kaynağı (İş 6 katkı seam'i).
    sentences: SentenceSource | None = None

    def command(self, name: str) -> Command | None:
        """Adiyla bir komut bulur; yoksa `None`."""
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None
