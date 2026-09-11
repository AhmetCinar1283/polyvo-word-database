"""
Cloze ipucu/aciklama cevirisinin icerik kapisi — HEPSI YA DA HIC.

Ipuclarinda zaten sik kelimesi gecmez (rationale QA'si bunu reddeder), bu
yuzden dil kapisi ipuclarinda DOGRUDAN calisir. Aciklamalarda ise sikkin
kendi INGILIZCE kelimesi BILEREK cevrilmeden kalir (Is 4 §14) — dil
kapisindan ONCE o kelime metinden cikarilir, yoksa dogru bir ceviri "model
cevirmemis" sanilip reddedilir (§16, `es` pilotunda 3 birim boyle
kaybedildi).
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze.translate import language

#: Dil kapisinin gecerli oldugu en kucuk kelime sayisi (Is 4 §14 deseni).
MIN_WORDS_FOR_LANG_GATE = 1


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _strip_known_word(text: str, word: str) -> str:
    """§16: dil kapisindan ONCE sikkin bilinen Ingilizce kelimesini cikarir."""
    pattern = re.compile(r"\b" + re.escape(word.strip()) + r"\b", re.IGNORECASE)
    return pattern.sub("", text)


def _fails_language_gate(translated: str, l1: str,
                         known_word: str | None) -> bool:
    """`translated` L1'e cevrilmemis mi — bilinen kelime cikarildiktan sonra."""
    probe = translated
    if known_word:
        probe = _strip_known_word(probe, known_word)
    return (len(probe.split()) >= MIN_WORDS_FOR_LANG_GATE
           and language.looks_english_not_l1(probe, l1))


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    hints = sorted(unit.data["hints"], key=lambda h: h["seq"])
    reasons = sorted(unit.data["reasons"], key=lambda r: (r["seq"], r["opt_seq"]))

    raw_hints = parsed.get("hints")
    raw_reasons = parsed.get("reasons")
    if not isinstance(raw_hints, list) or len(raw_hints) != len(hints):
        return QaResult(False, "ipucu_sayisi_uyusmuyor")
    if not isinstance(raw_reasons, list) or len(raw_reasons) != len(reasons):
        return QaResult(False, "aciklama_sayisi_uyusmuyor")

    translated_hints = [_text(h) for h in raw_hints]
    translated_reasons = [_text(r) for r in raw_reasons]
    if any(not h for h in translated_hints) or any(not r for r in translated_reasons):
        return QaResult(False, "bos_metin")

    for source, translated in zip(hints, translated_hints):
        if translated.strip().lower() == source["hint"].strip().lower():
            return QaResult(False, "ceviri_yapilmamis")
        if _fails_language_gate(translated, l1, known_word=None):
            return QaResult(False, "l1_ceviri_yapilmamis")

    for source, translated in zip(reasons, translated_reasons):
        if translated.strip().lower() == source["reason"].strip().lower():
            return QaResult(False, "ceviri_yapilmamis")
        if _fails_language_gate(translated, l1, known_word=source["text"]):
            return QaResult(False, "l1_ceviri_yapilmamis")

    warnings: list[str] = []
    all_translated = translated_hints + translated_reasons
    # UYARI, red degil: ayni metni iki kez uretmek bir bicim hatasi degil,
    # kalite sinyalidir.
    if len({text_qa.normalized_hash_text(t) for t in all_translated}) < len(all_translated):
        warnings.append("cevrilen_metinler_ayni")

    return QaResult(True, "; ".join(warnings) or None, payload={
        "hints": translated_hints, "reasons": translated_reasons})
