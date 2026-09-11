"""
Kapali kural sozlugunun okuma yuzeyi + denetimi.

`resolve` `merged_into` ZINCIRINI okuma aninda cozer: depoda ham id KALIR,
birlestirme geri alinabilir ve tek satir LLM parasi harcatmaz (§8). Zincir
DONGUYE girerse `CatalogError` — kapi burada duser.
"""

from __future__ import annotations

from polyvo.modules.grammar.catalog.model import AREAS, GrammarRule, is_valid_id
from polyvo.modules.grammar.catalog.rules import RULES, all_rules

__all__ = [
    "AREAS", "GrammarRule", "is_valid_id", "RULES", "all_rules",
    "CatalogError", "get", "resolve", "audit",
]

#: `merged_into` zincirinde bir dongu bulununca ne kadar adim sonra pes
#: edilir — katalogdaki kural sayisindan FAZLA adim demek dongu demektir.
_MAX_CHAIN = len(RULES) + 1


class CatalogError(RuntimeError):
    """Katalog tutarsiz: bilinmeyen id, bozuk `merged_into` ya da dongu."""


def get(rule_id: str) -> GrammarRule | None:
    """Id'siyle bir kural; katalogda yoksa `None`."""
    return RULES.get(rule_id)


def resolve(rule_id: str) -> GrammarRule:
    """`rule_id`nin `merged_into` ZINCIRINI cozup NIHAI kurali dondurur.

    Katalogda olmayan bir id ya da dongu `CatalogError` fırlatır — cagiran
    (QA, panel, export) bunu ayirt etmek zorunda degildir, ikisi de "bu id
    guvenilir degil" demektir."""
    seen: list[str] = []
    current = rule_id
    for _ in range(_MAX_CHAIN):
        if current in seen:
            raise CatalogError(
                f"merged_into dongusu: {' -> '.join(seen + [current])}")
        seen.append(current)
        rule = RULES.get(current)
        if rule is None:
            raise CatalogError(f"katalogda olmayan kural id'si: {current}")
        if rule.merged_into is None:
            return rule
        current = rule.merged_into
    raise CatalogError(f"merged_into zinciri cozulemedi: {rule_id}")


def audit() -> list[str]:
    """Katalogun kendi ic tutarliligi — bicim + `merged_into` hedefi +
    dongu + yinelenen id. Bos liste = katalog saglikli."""
    problems: list[str] = []
    for rule_id, rule in RULES.items():
        if rule_id != rule.id:
            problems.append(f"sozluk anahtari id'yle uyusmuyor: {rule_id}")
        if not is_valid_id(rule.id):
            problems.append(f"gecersiz id bicimi: {rule.id}")
        if rule.merged_into is not None and rule.merged_into not in RULES:
            problems.append(
                f"{rule.id}: merged_into bilinmeyen id'ye isaret ediyor: "
                f"{rule.merged_into}")
    for rule_id in RULES:
        try:
            resolve(rule_id)
        except CatalogError as exc:
            problems.append(str(exc))
    return problems
