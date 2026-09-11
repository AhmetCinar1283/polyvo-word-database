"""
Icerik kapisi — modelin cevabini kabul/red eder ve depoya girecek TEMIZ yuku
uretir. Motorun bildigi tek dogrulama yeri burasidir.

Yalnizca INGILIZCE karta bakar: ana dil karsiligi bu kartin parcasi degil,
ayri bir kosunun isidir (`translate/qa/`). Modelin cevabinda `gloss_l1` gelse
bile buradan gecmez — odenmis bir kart, cevirisi yuzunden reddedilemez.
Ayni sebeple `usage_note` da BURADA ISTENMEZ/YAZILMAZ (Is 3) — tek ureticisi
`note/qa.py`dir.

Ayrim onemli: REDDEDEN kontroller garanti edilebilir olanlardir (alan eksik,
gloss kelimenin kendisi, ornek sayisi). Garanti edilemeyen kontroller (ornek
cumlede hedef kelime gorunuyor mu — cekim/turetme tam cozulemez) REDDETMEZ,
`reason`a UYARI yazar (§6.7): yanlis reddin maliyeti yanlis kabulden yuksektir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.lexicon_card.prompt import EXAMPLE_COUNT, REGISTERS

#: Tanim bu uzunlugu asarsa aciklamaya donmustur, sozluk glossu degildir.
MAX_GLOSS_EN_CHARS = 220
MIN_EXAMPLE_WORDS = 4


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _examples(value) -> list[str]:
    """Ornek listesini temizler; liste degilse bos doner."""
    if not isinstance(value, list):
        return []
    return [_text(v) for v in value if _text(v)]


def run(parsed: dict | None, unit: Unit) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    headword = unit.data["headword"]

    gloss_en = _text(parsed.get("gloss_en"))
    if not gloss_en:
        return QaResult(False, "gloss_en_bos")
    if len(gloss_en) > MAX_GLOSS_EN_CHARS:
        return QaResult(False, "gloss_en_cok_uzun")
    if text_qa.mentions_target(gloss_en, headword):
        return QaResult(False, "gloss_en_kelimenin_kendisini_iceriyor")

    examples = _examples(parsed.get("examples"))
    if len(examples) < EXAMPLE_COUNT:
        return QaResult(False, "ornek_sayisi_yetersiz")
    examples = examples[:EXAMPLE_COUNT]
    if any(len(ex.split()) < MIN_EXAMPLE_WORDS for ex in examples):
        return QaResult(False, "ornek_cumle_cok_kisa")
    if len({text_qa.normalized_hash_text(ex) for ex in examples}) < len(examples):
        return QaResult(False, "ornekler_ayni")

    register = _text(parsed.get("register")).lower()
    warnings = []
    if register not in REGISTERS:
        warnings.append("register_taninmadi_neutral_yazildi")
        register = "neutral"
    # UYARI, red degil: cekim/turetme tam cozulemedigi icin garanti edilemez.
    if not all(text_qa.mentions_target(ex, headword) for ex in examples):
        warnings.append("ornekte_hedef_kelime_bulunamadi")

    return QaResult(True, "; ".join(warnings) or None, payload={
        "gloss_en": gloss_en,
        "register": register,
        "examples": examples,
    })
