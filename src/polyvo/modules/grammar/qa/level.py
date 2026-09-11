"""
SEVIYE + SIRALAMA kapisi — Is 6 §13'un UYARAN yarisi + §14. IKISI DE
REDDETMEZ, yalnizca UYARIR.

Seviye: cumlenin/anlamin CEFR'i kuralin `assume_known_from` bandinin
USTUNDEYSE ogrenci icin "goze carpan" olmaktan cikmis olabilir — ama 1000
kelimenin 160'inda CEFR YOK (Is 4 §10) ve "bu ogrenci bunu biliyor" GARANTI
EDILEMEZ, bu yuzden REDDETMEZ.

Siralama: "gercekten en goze carpan bu mu" sorusunun MEKANIK yaniti YOKTUR
(gomme katmani yok, Is 4'teki "celdirici gercekten uymuyor mu" riskinin
IKIZI). Bu yuzden HER onayli pakete SABIT bir uyari duser ve pilotta ELLE
okunur (Is 6 §14) — kesinlikle RED yapilmaz.
"""

from __future__ import annotations

from polyvo.modules.grammar import levels
from polyvo.modules.grammar.catalog import get

#: Her onayli pakete SABIT dusen uyari — sirlamanin dogrulugu OLCULEMEZ.
RANKING_UNVERIFIED = "siralamanin_dogrulugu_olculemedi"


def check(sentences: list[dict], unit) -> tuple[str | None, list[str]]:
    """Asla reddetmez; seviye-ustu kural + sabit siralama uyarisini toplar."""
    warnings: list[str] = []
    for s in sentences:
        cefr = s.get("cefr")
        for rule in s["rules"]:
            catalog_rule = get(rule["rule_id"])
            if catalog_rule is None:
                continue
            if levels.exceeds(cefr, catalog_rule.assume_known_from):
                warnings.append(
                    f"kural_seviye_ustu: {rule['rule_id']} ({s['ref']})")
    warnings.append(RANKING_UNVERIFIED)
    return None, warnings
