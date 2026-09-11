"""
"Cevap Ingilizce isaretleri tasiyip L1 isaretcisi tasimiyor mu" sinyali —
TEK tanim yeri. `l1_form.py` (kelime karsiligi, KISA cevap) ve
`translate/qa/entry.py` (tanim + ornekler, UZUN cevap) ayni sinyali kullanir;
red/uyari esigi CAGIRANDAN gelir (kisa cevapta tek kelime islev sozcugu tek
basina ayirt edici degildir — bkz. `l1_form.py::MIN_WORDS_FOR_LANG_GATE`
olcumu), bu yuzden burada sabitlenmez.
"""

from __future__ import annotations

from polyvo.core.lang import get_rules
from polyvo.core.text import qa as text_qa


def looks_english_not_l1(text: str, l1: str) -> bool:
    """Metin AYIRT EDICI Ingilizce isareti tasiyip dilin KENDI isaretcisini
    TASIMIYORSA `True`. Dilin isaretcisi tanimsizsa (`LANG_MARKERS=None`) hep
    `False`.

    "Ayirt edici" sarti 2026-09-07'de eklendi: hedef dilde DE gecen isaretci
    (`a`/`no`/`in`) Ingilizce kaniti SAYILMAZ (`ENGLISH_AMBIGUOUS`). Oncesinde
    kapinin Ingilizce yarisi pratikte HER metinde ateslendigi icin karar tek
    basina L1 isaretcisine kaliyordu ve dogru ceviriler reddediliyordu."""
    rules = get_rules(l1)
    if rules.LANG_MARKERS is None:
        return False
    if rules.LANG_MARKERS.search(text):
        return False
    return text_qa.english_marker_hits(text, rules.ENGLISH_AMBIGUOUS) > 0
