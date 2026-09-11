"""
ASIKARLIK kapisi — Is 6 §13'ün REDDEDEN yarisi.

`trivial=True` bir kural (kopula, tanimlik, cogul -s gibi) HER siradan
cumlede vardir; `rank=1`de gelmesi "bu cumlenin tasiyici yapisi budur"
demektir ve bu YANLIS bir iddiadir — olculebilir, tartismasiz REDDEDER.
`rank>=2`de aynı kural GECER: ayrinti listesinde durmasinda sakinca yoktur.
"""

from __future__ import annotations

from polyvo.modules.grammar.catalog import get


def check(sentences: list[dict], unit) -> tuple[str | None, list[str]]:
    """Herhangi bir cumlede `rank=1` kural `trivial=True` mi? Oyleyse TUM
    grup reddedilir."""
    for s in sentences:
        for rule in s["rules"]:
            if rule["rank"] != 1:
                continue
            catalog_rule = get(rule["rule_id"])
            # Katalogda bulunmama durumu `catalog.py`de zaten REDDEDILDI —
            # buraya `None` gelmez, yine de savunmaci davranilir.
            if catalog_rule is not None and catalog_rule.trivial:
                return f"trivial_kural_rank_1de: {rule['rule_id']}", []
    return None, []
