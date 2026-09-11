"""
Grammar not cevirisinin icerik kapisi — HEPSI YA DA HIC.

`trigger` metinleri BILEREK cevrilmeden kalir (Is 6 §18); model notun
ICINE trigger'i (Ingilizce) yazmis olabilir (aciklama amacli). Dil
kapisindan ONCE o metin CIKARILIR — yoksa dogru bir ceviri "model
cevirmemis" sanilip reddedilir (§16/§18, `es` pilotunda 3 birim boyle
kaybedilmisti — cloze/rationale aynı tuzağı, aynı düzeltmeyle kapattı).
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.grammar.translate import language

#: Dil kapisinin gecerli oldugu en kucuk kelime sayisi.
MIN_WORDS_FOR_LANG_GATE = 1


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _strip_trigger(text: str, trigger: str) -> str:
    """§18: dil kapisindan ONCE bilinen `trigger` metnini cikarir."""
    pattern = re.compile(r"\b" + re.escape(trigger.strip()) + r"\b",
                         re.IGNORECASE)
    return pattern.sub("", text)


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    items = unit.data["rules"]
    raw = parsed.get("notes")
    if not isinstance(raw, list) or len(raw) != len(items):
        return QaResult(False, "not_sayisi_uyusmuyor")

    translated = [_text(t) for t in raw]
    if any(not t for t in translated):
        return QaResult(False, "bos_metin")

    for source, text in zip(items, translated):
        if text.strip().lower() == source["note"].strip().lower():
            return QaResult(False, "ceviri_yapilmamis")
        probe = _strip_trigger(text, source["trigger"])
        if len(probe.split()) >= MIN_WORDS_FOR_LANG_GATE and \
                language.looks_english_not_l1(probe, l1):
            return QaResult(False, "l1_ceviri_yapilmamis")

    warnings: list[str] = []
    # UYARI, red degil: ayni metni iki kez uretmek bir bicim hatasi degil,
    # kalite sinyalidir.
    if len({text_qa.normalized_hash_text(t) for t in translated}) < len(translated):
        warnings.append("cevrilen_notlar_ayni")

    return QaResult(True, "; ".join(warnings) or None,
                    payload={"notes": translated})
