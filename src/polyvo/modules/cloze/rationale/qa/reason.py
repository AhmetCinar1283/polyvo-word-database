"""
ACIKLAMA kapilari — sik basina, dogru cevap dahil dordu de.

Cloze `qa/distractor.py` ile AYNI gerekce (§6.7): "celdiricinin aciklamasi
DOGRU mu" mekanik olarak dogrulanamaz — o kontrol burada YOKTUR, her onayli
pakete bir UYARI dusurulur, KESINLIKLE reddedilmez. Sayilabilen UC sey
REDDEDER: uzunluk bandi, aciklamanin kendi sikkinin kelimesini icermesi
(V2-IS-5 §14 "ucuz kural"), ve dort aciklamanin normalize edildiginde
ayirt edilebilir olmasi.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze.difficulty import OPTION_COUNT
from polyvo.modules.cloze.rationale.shape import REASON_BAND


def _word_count(text: str) -> int:
    """Basit kelime sayimi — bant kontrolu icin yeterli."""
    return len(text.split())


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) doner."""
    warnings: list[str] = []
    for question in questions:
        seen_hashes: set[str] = set()
        for item in question["reasons"]:
            n = _word_count(item["reason"])
            if not (REASON_BAND.min_words <= n <= REASON_BAND.max_words):
                return "aciklama_uzunluk_bandi_disinda", warnings
            if not text_qa.mentions_target(item["reason"], item["text"]):
                return "aciklama_kendi_sikkinin_kelimesini_icermiyor", warnings
            seen_hashes.add(text_qa.normalized_hash_text(item["reason"]))
        if len(seen_hashes) < OPTION_COUNT:
            return "dort_aciklama_ayni_kalip", warnings

    # HER pakete dusen, ASLA reddetmeyen uyari — bkz. modul docstring'i.
    warnings.append("celdirici_aciklamasi_dogrulanamadi")
    return None, warnings
