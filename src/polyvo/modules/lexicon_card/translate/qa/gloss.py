"""
Paketin KARSILIK parcasinin (`gloss_l1` + `gloss_note`) kapisi — eski
`gloss/qa.py`, kapilari degismeden tasindi.

Dil + sozluk-bicimi kontrolu `lexicon_card/l1_form.py`den gelir — kart
QA'siyla AYNI tanim, ikinci bir kural kumesi burada yazilmaz.

REDDEDEN kontroller garanti edilebilir olanlardir: alan bos, cevap cumleye
donmus, model kartin Ingilizce TANIMINI aynen geri dondurmus. Karsiligin
kelimenin KENDISIYLE ayni olmasi garanti edilemez — `hotel`/`animal`/`no`
gibi es kokenli ve islev sozcuklerinde dogru cevap tam olarak budur — bu
yuzden REDDETMEZ, uyarir (§6.7).

`gloss_note` (Is 3 madde 9) icin TEK olculebilir kapi: not karsiligin
KENDISIYLE neredeyse ayniysa RED — o zaman not bir aciklama degil, karsiligin
tekrari, gerceklik payi tasimiyor demektir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.lexicon_card import l1_form

#: L1 karsiligi bundan uzunsa cumle yazilmis demektir, karsilik degil.
MAX_GLOSS_L1_CHARS = 80

#: Not bu uzunlugu asarsa aciklamaya donmustur, kisa not degil.
MAX_GLOSS_NOTE_CHARS = 160


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    gloss_l1 = _text(parsed.get("gloss_l1"))
    if not gloss_l1:
        return QaResult(False, "gloss_l1_bos")
    if len(gloss_l1) > MAX_GLOSS_L1_CHARS:
        return QaResult(False, "gloss_l1_karsilik_degil_cumle")

    headword = unit.data["headword"]
    card = unit.data["card"]
    lowered = gloss_l1.lower()
    warnings: list[str] = []

    # Model ceviri yerine kartin TANIMINI geri dondurmus: bu garanti edilebilir.
    if lowered == card["gloss_en"].strip().lower():
        return QaResult(False, "gloss_l1_kart_kopyasi")
    # Kelimenin kendisi: es kokenli sozcukte DOGRU cevap olabilir -> uyari.
    if lowered == headword.lower():
        warnings.append("l1_karsilik_kelimenin_kendisiyle_ayni")

    form = l1_form.check(gloss_l1, unit.data["pos"], l1)
    if form.reject:
        return QaResult(False, form.reject)
    warnings.extend(form.warnings)

    gloss_note = _text(parsed.get("gloss_note"))
    if gloss_note:
        if len(gloss_note) > MAX_GLOSS_NOTE_CHARS:
            return QaResult(False, "gloss_notu_cok_uzun")
        if gloss_note.strip().lower() == lowered:
            return QaResult(False, "gloss_notu_karsiligin_kopyasi")

    return QaResult(True, "; ".join(warnings) or None,
                    payload={"gloss_l1": gloss_l1, "gloss_note": gloss_note})
