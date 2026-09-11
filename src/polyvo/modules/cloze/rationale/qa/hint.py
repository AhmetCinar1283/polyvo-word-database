"""
IPUCU kapilari — cevabi VERMEZ, yol GOSTERIR (V2-IS-5 §8).

Sayilabilir UC sey REDDEDER: dogru cevabin (bir bicimiyle) veya herhangi bir
sikkin metninin birebir gecmesi, uzunluk bandinin disinda kalmak, ve sikka
KONUMUYLA gonderme yapmak ("first option", "B sikki"). "Ipucu gercekten
yardimci mi, fazla mi acik ediyor" ise OLCULEMEZ — bu dosyada YOKTUR,
`qa/__init__.py` orkestrasyonu bu kapiyi UYARIYA bile dusurmez cunku hicbir
mekanik olcek yoktur.
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze.rationale.shape import HINT_BAND

#: Sikka KONUMUYLA gonderme yapan kapali kalip listesi. Ipucu bu asamada
#: henuz cevrilmemis Ingilizcedir, bu yuzden liste Ingilizcedir.
_POSITION_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bfirst option\b", r"\bsecond option\b", r"\bthird option\b",
    r"\bfourth option\b", r"\boption [a-d]\b",
    r"\boption (one|two|three|four)\b",
    r"\b(1st|2nd|3rd|4th) option\b", r"\bletter [a-d]\b",
))


def _word_count(text: str) -> int:
    """Basit kelime sayimi — bant kontrolu icin yeterli."""
    return len(text.split())


def _mentions_literal_option(hint: str, option_text: str) -> bool:
    """Ipucu, sikkin metnini BIREBIR (tam kelime/ifade) iceriyor mu."""
    pattern = re.compile(r"\b" + re.escape(option_text.strip().lower()) + r"\b")
    return bool(pattern.search(hint.lower()))


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) doner — bu kapi HICBIR UYARI uretmez."""
    headword = unit.data["headword"]
    for question in questions:
        hint = question["hint"]
        n = _word_count(hint)
        if not (HINT_BAND.min_words <= n <= HINT_BAND.max_words):
            return "ipucu_uzunluk_bandi_disinda", []
        if text_qa.mentions_target(hint, headword):
            return "ipucu_dogru_cevabi_iceriyor", []
        for option in question["options"]:
            if _mentions_literal_option(hint, option):
                return "ipucu_sik_metnini_iceriyor", []
        if any(p.search(hint) for p in _POSITION_PATTERNS):
            return "ipucu_konuma_gonderme_yapiyor", []
    return None, []
