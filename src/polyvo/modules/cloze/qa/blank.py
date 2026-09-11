"""
BOSLUK kapisi — hedef kelime cumlede gercekten var mi, TAM BIR KEZ mi, ve
dogru cevap cumledeki bicimin kendisi mi.

Bu kapinin dayanagi `core/text/qa.py::find_spans_loose`tir: duzenli cekim
(regex) + duzensiz cekim (WordNet `morphy`). Burada kelimenin yalnizca
VARLIGI degil KONUMU gerekir — cloze icin ayirt edici olan budur.

Neden "tam bir kez": kelime iki kez geciyorsa boslugu hangi gecisin
olusturdugu belirsizdir; sifir kez geciyorsa ortada cloze yoktur. Ikisi de
sayilabilir, ikisi de REDDEDER.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa

#: Boslugun gosterimde alacagi isaret (`render.py` de bunu kullanir).
BLANK_MARK = "____"


def answer_span(sentence: str, headword: str) -> tuple[int, int, str] | None:
    """Cumledeki hedef kelimenin (baslangic, bitis, yuzey bicim)i; yoksa `None`."""
    spans = text_qa.find_spans_loose(sentence, headword)
    return spans[0] if len(spans) == 1 else None


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) dondurur."""
    headword = unit.data["headword"]
    warnings: list[str] = []

    for question in questions:
        sentence = question["sentence"]
        spans = text_qa.find_spans_loose(sentence, headword)
        if not spans:
            return "hedef_kelime_cumlede_yok", warnings
        if len(spans) > 1:
            return "hedef_kelime_cumlede_birden_cok_kez", warnings

        start, end, surface = spans[0]
        if question["answer"].strip().lower() != surface.lower():
            return "dogru_cevap_cumledeki_bicim_degil", warnings

        # Duzenli cekim regex'i tutmadiysa esleme WordNet kokunden gelmistir:
        # cekim COZULDU ama emin degiliz -> UYARI (§6.7), red degil.
        if not text_qa.find_spans(sentence, headword):
            warnings.append(f"cekim_gevsek_eslesti_seq{question['seq']}")

        question["blank_start"] = start
        question["blank_end"] = end

    return None, warnings
