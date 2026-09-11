"""
Katalog aciklamasi cevirisinin icerik kapisi — HEPSI YA DA HIC.

`trigger` burada YOK (katalog cumleye ozel degildir) — §18'in cikarma
adimina GEREK KALMAZ, dil kapisi metne DOGRUDAN uygulanir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.grammar.translate import language

#: Dil kapisinin gecerli oldugu en kucuk kelime sayisi.
MIN_WORDS_FOR_LANG_GATE = 1


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    name = _text(parsed.get("name"))
    short = _text(parsed.get("short"))
    if not name or not short:
        return QaResult(False, "bos_metin")

    source_name = unit.data["name_en"].strip().lower()
    source_short = unit.data["short_en"].strip().lower()
    if name.lower() == source_name and short.lower() == source_short:
        return QaResult(False, "ceviri_yapilmamis")

    for text in (name, short):
        if len(text.split()) >= MIN_WORDS_FOR_LANG_GATE and \
                language.looks_english_not_l1(text, l1):
            return QaResult(False, "l1_ceviri_yapilmamis")

    return QaResult(True, None, payload={"name": name, "short": short})
