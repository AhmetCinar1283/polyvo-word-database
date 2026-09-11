"""
TEKDUZELIK kapisi — bir anlamin uc cumlesi ayni acilis kalibiyla baslayamaz.

Gecmis sikayet olculdu: uretilen cumleler birbirine benziyor ("I eat cake"
tekduzeligi). Bu, "cesitli ol" diye yazarak degil SAYARAK engellenir; acilis
n-gram'i sayilabilir oldugu icin bu kapi REDDEDER.

Ucunun de birbirine benzemesi (ayni sahne hissi, ayni kalip ama farkli
kelimeler) sayilamaz -> UYARI degil, hic olculmez; onun araci sahne kisitidir
(`scene.py`).
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import Unit

#: Acilis kalibi kac kelimeden sayilir.
OPENING_WORDS = 3

_WORD_RE = re.compile(r"[a-z']+")


def opening_ngram(sentence: str, size: int = OPENING_WORDS) -> str:
    """Cumlenin acilis n-gram'i (kucuk harf, noktalamasiz). Panel de bunu
    kullanir — tekduzelik sayimi ile QA kapisi AYNI tanimi paylasir."""
    words = _WORD_RE.findall((sentence or "").lower())
    return " ".join(words[:size])


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) dondurur."""
    openings = [opening_ngram(q["sentence"]) for q in questions]
    if len({o for o in openings if o}) < len([o for o in openings if o]):
        return "uc_cumle_ayni_acilis_kalibi", []
    return None, []
