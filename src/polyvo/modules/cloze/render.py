"""
Bosluklu GORUNUM — depoda tam cumle durur, bosluk gosterimde uretilir.

Neden depoda tam cumle: cevirisi "boslugu doldurulmus tam cumlenin" cevirisi
olmalidir (§14). Boslugu depoya yazsaydik, ceviri icin cumleyi geri kurmak
gerekirdi.
"""

from __future__ import annotations

from polyvo.modules.cloze.qa.blank import BLANK_MARK, answer_span


def blanked(sentence: str, headword: str) -> str:
    """Hedef kelimenin yerine bosluk konmus cumle; bulunamazsa cumle aynen."""
    span = answer_span(sentence, headword)
    if span is None:
        return sentence
    start, end, _surface = span
    return sentence[:start] + BLANK_MARK + sentence[end:]
