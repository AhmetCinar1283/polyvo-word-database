"""
SEVIYE kapilari — cumle uzunlugu ve kelime dagarcigi.

Uzunluk her zaman olculur ve REDDEDER: zorluk bandi (`difficulty.py`) prompt'a
yazilan sozun kendisidir, tutulmadiysa soru istenen soru degildir.

Kelime dagarcigi YALNIZCA CEFR BILINIYORSA olculur. 1000 kelimenin 160'inda
`cefr` yok; **bilinmeyen seviye bir red gerekcesi degildir** (§10) — "bilmiyorum"
bir satiri cope attirmaz, uyari birakir.

Cumlenin kendi seviyesine USLUP olarak uygunlugu olculemez (§11) — uzunluk ve
kelime dagarcigi olculur, uslup olculmez.
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze import cefr
from polyvo.modules.cloze.difficulty import band_for

#: Modelin "about N-M words" yonergesini yorumlamasina birakilan pay. Sifir
#: tolerans, dogru bir soruyu tek kelime yuzunden odenmis halde cope atardi.
#:
#: BU PAY YALNIZCA BURADA GENISLER, PROMPT'TA DEGIL: modele dar bandi
#: soyleriz (`difficulty.BANDS`), olcerken payi biz veririz. Genis bandi
#: modele soylemek bandin ORTASINI kaydirirdi — model sinira degil, soylenen
#: araligin ortasina nisan alir. 2026-09-07 kosusunda reddedilen "zor"
#: cumleler 13 kelimeydi, bandin alt siniri 15.
WORD_COUNT_TOLERANCE = 3

_WORD_RE = re.compile(r"[A-Za-z']+")


def _content_words(sentence: str, headword: str) -> list[str]:
    """Cumlenin ICERIK kelimeleri: islev sozcukleri ve hedef kelime cikarilir.

    Islev sozcugu listesi `core/text/qa.py::ENGLISH_MARKERS`tir — ayni tanim
    iki yerde yazilmasin diye oradan gelir."""
    out = []
    for token in _WORD_RE.findall(sentence):
        low = token.lower()
        if text_qa.ENGLISH_MARKERS.fullmatch(low):
            continue
        if text_qa.loose_same_word(low, headword):
            continue
        out.append(low)
    return out


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) dondurur."""
    headword = unit.data["headword"]
    sense_cefr = unit.data.get("cefr")
    levels = cefr.load(unit.data["cefr_db"])
    warnings: list[str] = []

    if not sense_cefr:
        warnings.append("anlamin_cefri_bilinmiyor_kelime_dagarcigi_olculmedi")

    for question in questions:
        band = band_for(question["seq"])
        count = len(_WORD_RE.findall(question["sentence"]))
        if not (band.min_words - WORD_COUNT_TOLERANCE
                <= count <= band.max_words + WORD_COUNT_TOLERANCE):
            return "cumle_uzunlugu_zorluk_bandi_disinda", warnings

        if not sense_cefr:
            continue
        for word in _content_words(question["sentence"], headword):
            word_cefr = levels.get(word)
            if word_cefr is None:
                continue                  # evren disi kelime: olcum yok, red yok
            # Celdirici tavaniyla AYNI pay: bir A1 anlamin 15-25 kelimelik
            # "zor" cumlesi yalnizca A1 kelimeyle kurulamaz.
            if cefr.exceeds(word_cefr, sense_cefr, cefr.LEVEL_TOLERANCE):
                return "cumlede_anlamin_seviyesinin_ustunde_kelime", warnings

    return None, warnings
