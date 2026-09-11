"""
"Ceviri yapilmamis, metin hala Ingilizce" sinyali.

NEDEN BURADA: ayni sinyalin bir kopyasi `lexicon_card` icinde de var
(`l1_language.py`). App'ler birbirini import edemez (demir kural) ve bu isin
kapsami `lexicon_card`in uretim dosyalarina dokunmayi YASAKLIYOR, bu yuzden
paylasilan sey fonksiyon degil ALTINDAKI IKI CORE PARCASIDIR:
`core/text/qa.py::ENGLISH_MARKERS` ve `core/lang/<kod>.LANG_MARKERS`.

Temiz cozum bu fonksiyonun `core/lang/`e tasinmasidir; iki app de oradan
okur. O tasima `lexicon_card`i degistirecegi icin AYRI bir isin konusudur.
"""

from __future__ import annotations

from polyvo.core.lang import get_rules
from polyvo.core.text import qa as text_qa


def looks_english_not_l1(text: str, l1: str) -> bool:
    """Metin AYIRT EDICI Ingilizce isareti tasiyip dilin KENDI isaretcisini
    TASIMIYORSA `True`. Dilin isaretcisi tanimsizsa (`LANG_MARKERS=None`) hep
    `False` — kuralsiz bir dil sessizce reddedilmez.

    "Ayirt edici" sarti icin bkz. `core/text/qa.py::english_marker_hits`:
    hedef dilde DE gecen isaretci (`a`/`no`/`in`) Ingilizce kaniti sayilmaz."""
    rules = get_rules(l1)
    if rules.LANG_MARKERS is None:
        return False
    if rules.LANG_MARKERS.search(text):
        return False
    return text_qa.english_marker_hits(text, rules.ENGLISH_AMBIGUOUS) > 0
