"""
Bir grubun (birden fazla cumlenin) prompt'a giden CEFR tavani.

Yalnizca prompt'un katalog listesini KISALTMAK icindir — bir kapi DEGILDIR
(hicbir sey reddetmez); asil seviye kapisi `qa/level.py`de, CUMLE basina
calisir. Burada grubun EN YUKSEK bilinen seviyesi alinir (permissif): bir
sonraki asamada hangi cumlenin hangi kurala ihtiyaci oldugunu modelin kendisi
secer, listede fazla kural olmasi zarasizdir.
"""

from __future__ import annotations

from polyvo.modules.grammar.levels import rank


def ceiling_for(sentences: list[dict]) -> str | None:
    """Gruptaki cumlelerin EN YUKSEK bilinen CEFR'i; hicbiri bilinmiyorsa
    `None` (katalog hic filtrelenmez)."""
    best: str | None = None
    best_order: int | None = None
    for s in sentences:
        order = rank(s.get("cefr"))
        if order is not None and (best_order is None or order > best_order):
            best, best_order = s["cefr"], order
    return best
