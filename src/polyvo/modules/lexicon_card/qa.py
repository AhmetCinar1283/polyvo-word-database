"""
Icerik kapisi — modelin cevabini kabul/red eder ve depoya girecek TEMIZ yuku
uretir. Motorun bildigi tek dogrulama yeri burasidir.

Ayrim onemli: REDDEDEN kontroller garanti edilebilir olanlardir (alan eksik,
gloss kelimenin kendisi, ceviri yapilmamis, L1 bicimi bozuk). Garanti
edilemeyen kontroller (ornek cumlede hedef kelime gorunuyor mu — cekim/
turetme tam cozulemez) REDDETMEZ, `reason`a UYARI yazar (§6.7): yanlis
reddin maliyeti yanlis kabulden yuksektir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.lang import get_rules
from polyvo.core.text import qa as text_qa
from polyvo.modules.lexicon_card.prompt import EXAMPLE_COUNT, REGISTERS

#: Tanim bu uzunlugu asarsa aciklamaya donmustur, sozluk glossu degildir.
MAX_GLOSS_EN_CHARS = 220
#: L1 karsiligi bundan uzunsa cumle yazilmis demektir, karsilik degil.
MAX_GLOSS_L1_CHARS = 80
MIN_EXAMPLE_WORDS = 4


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _examples(value) -> list[str]:
    """Ornek listesini temizler; liste degilse bos doner."""
    if not isinstance(value, list):
        return []
    return [_text(v) for v in value if _text(v)]


def _check_l1(gloss_l1: str, pos: str, l1: str) -> str | None:
    """L1 karsiliginin dili ve sozluk bicimi kapisi; sorun varsa kisa kod."""
    rules = get_rules(l1)
    # Model cevirmeyip Ingilizce'yi aynen geri dondurmus mu?
    markers = rules.LANG_MARKERS
    if markers is not None and not markers.search(gloss_l1) \
            and text_qa.ENGLISH_MARKERS.search(gloss_l1):
        return "l1_ceviri_yapilmamis"
    return rules.check_form(pos, gloss_l1)


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    headword = unit.data["headword"]
    pos = unit.data["pos"]

    gloss_en = _text(parsed.get("gloss_en"))
    if not gloss_en:
        return QaResult(False, "gloss_en_bos")
    if len(gloss_en) > MAX_GLOSS_EN_CHARS:
        return QaResult(False, "gloss_en_cok_uzun")
    if text_qa.mentions_target(gloss_en, headword):
        return QaResult(False, "gloss_en_kelimenin_kendisini_iceriyor")

    gloss_l1 = _text(parsed.get("gloss_l1"))
    if not gloss_l1:
        return QaResult(False, "gloss_l1_bos")
    if len(gloss_l1) > MAX_GLOSS_L1_CHARS:
        return QaResult(False, "gloss_l1_karsilik_degil_cumle")
    problem = _check_l1(gloss_l1, pos, l1)
    if problem:
        return QaResult(False, problem)

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
        "usage_note": _text(parsed.get("usage_note")),
        "gloss_l1": gloss_l1,
        "examples": examples,
    })
