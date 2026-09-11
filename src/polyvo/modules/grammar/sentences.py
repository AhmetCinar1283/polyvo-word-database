"""
Cumleleri KATKI SEAM'inden toplar — `grammar` hicbir kardes `modules/*`
paketini import ETMEZ. `discovery.find_apps()` her app'i gezer, `APP.
sentences` ilan eden her app'in `loader`ini cagirir.

`apps` parametresi bu genelligi TEST EDILEBILIR kilan tek seydir: gercek
kosuda hic verilmez (varsayilan `discovery.find_apps()`), testte SAHTE bir
`App` listesi verilir — boylece "besinci bir soru tipi tek satir degistirmez"
sozu bir mock DEGIL gercek kesif fonksiyonuyla da olculur.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.core.cli.app import App, SentenceGroup
from polyvo.core.cli.discovery import find_apps


@dataclass(frozen=True)
class OwnedGroup:
    """Bir `SentenceGroup` + onu sunan app'in adi (kimligin parcasi)."""
    owner: str
    group: SentenceGroup


def collect(tag: str, l2: str, apps: list[App] | None = None) -> list[OwnedGroup]:
    """Her app'in ilan ettigi cumle gruplarini `(owner, group_key)` sirasinda
    TOPLAR. `APP.sentences` olmayan app sessizce atlanir — bu bir hata degil,
    o app'in bu isle ilgisi yok demektir."""
    sources = apps if apps is not None else find_apps()
    out: list[OwnedGroup] = []
    for app in sources:
        source = app.sentences
        if source is None:
            continue
        for group in source.loader(tag, l2):
            out.append(OwnedGroup(owner=source.owner, group=group))
    out.sort(key=lambda item: (item.owner, item.group.group_key))
    return out
