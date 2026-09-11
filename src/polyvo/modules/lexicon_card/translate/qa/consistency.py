"""
Terim tutarliligi — karsilik (`gloss_l1`) ornek cumlelerde geciyor mu.

YALNIZCA UYARI, asla red (§6.7): cekim yuzunden garanti edilemez ("koşmak"
-> "koştular"). Yuzey karsilastirmasi `core/text/qa.py::loose_same_word`,
dil bayragi `core/lang/<l1>.TERM_MATCH_SUPPORTED` — bayragi acmayan dilde
(on ekli/olculmemis) bu kontrol hic calismaz.
"""

from __future__ import annotations

import re

from polyvo.core.lang import get_rules
from polyvo.core.text import qa as text_qa

WARNING = "gloss_terimi_orneklerde_yok"

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _mentions(sentence: str, gloss_words: list[str]) -> bool:
    """Cumlede karsiligin herhangi bir kelimesi (gevsek) geciyor mu?"""
    tokens = _WORD_RE.findall(sentence)
    return any(text_qa.loose_same_word(tok, word)
               for word in gloss_words for tok in tokens)


def check(gloss_l1: str, examples: list[str], l1: str) -> list[str]:
    """Karsilik bir ornekte bile gecmiyorsa uyari listesi; yoksa bos."""
    if not getattr(get_rules(l1), "TERM_MATCH_SUPPORTED", False):
        return []
    gloss_words = _WORD_RE.findall(gloss_l1)
    if not gloss_words:
        return []
    if all(_mentions(ex, gloss_words) for ex in examples):
        return []
    return [WARNING]
