"""
Katalog cevirisinin birimleri — katalogdaki HER kural icin bir birim
(cumle/grup DEGIL, KATALOG boyutu).

`merged_into` dolu olan kurallar ATLANIR: bunlar okuma aninda baska bir
id'ye COZULUR (bkz. `catalog/__init__.py::resolve`), kendileri hicbir yerde
GOSTERILMEZ — cevirisi bosa giden bir cagri olurdu.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.grammar import fingerprint
from polyvo.modules.grammar.catalog import all_rules


def load_units(tag: str, l2: str) -> list[Unit]:
    """`tag`/`l2` yalnizca `Job` sozlesmesi geregi alinir — katalog kod
    icinde durur, veri kosuya BAGLI degildir (ikisi de kullanilmaz)."""
    del tag, l2
    units: list[Unit] = []
    for rule in all_rules():
        if rule.merged_into is not None:
            continue
        units.append(Unit(
            key=rule.id,
            name=rule.id,
            data={
                "rule_id": rule.id,
                "name_en": rule.name_en,
                "short_en": rule.short_en,
                "catalog_sha256": fingerprint.catalog_sha256(rule),
            },
        ))
    return units
