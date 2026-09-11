"""
"Ceviri yapilmamis, metin hala Ingilizce" sinyali — `cloze/translate/
language.py`nin KUCUK bir KOPYASI (ayni iki `core/` parcasi ustunde).

NEDEN KOPYA: `grammar` hicbir kardes `modules/*` paketini import EDEMEZ
(demir kural). Paylasilan sey fonksiyon degil ALTINDAKI IKI CORE PARCASIDIR:
`core/text/qa.py::ENGLISH_MARKERS` ve `core/lang/<kod>.LANG_MARKERS`. Temiz
cozum bu fonksiyonun `core/lang/`e tasinmasidir — o tasima AYRI bir isin
konusudur (ayni tuzak `cloze/translate/language.py`nin docstring'inde de
kayitlidir).
"""

from __future__ import annotations

from polyvo.core.lang import get_rules
from polyvo.core.text import qa as text_qa


def looks_english_not_l1(text: str, l1: str) -> bool:
    """Metin AYIRT EDICI Ingilizce isareti tasiyip dilin KENDI isaretcisini
    TASIMIYORSA `True`. Dilin isaretcisi tanimsizsa (`LANG_MARKERS=None`) hep
    `False` — kuralsiz bir dil sessizce reddedilmez."""
    rules = get_rules(l1)
    if rules.LANG_MARKERS is None:
        return False
    if rules.LANG_MARKERS.search(text):
        return False
    return text_qa.english_marker_hits(text, rules.ENGLISH_AMBIGUOUS) > 0
