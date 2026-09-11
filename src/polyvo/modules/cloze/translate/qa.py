"""
Cloze cevirisinin icerik kapisi — HEPSI YA DA HIC.

Paketin tamami ayni isin, ayni dilin urunudur: eksik cumle bir BICIM
hatasidir, yeniden denenir. Ingilizce cloze tarafina HICBIR KOSULDA
dokunulmaz — reddedilen ceviri, odenmis Ingilizce soruyu cope atmaz.

Cumle UZUN bir metindir, bu yuzden dil kapisi burada 1 kelimeden itibaren
gecerlidir; kisa cevaptaki "ayirt edememe" sorunu (tek kelimelik islev
sozcugu) burada yoktur.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze.translate import language

#: Dil kapisinin gecerli oldugu en kucuk kelime sayisi (cumle = uzun metin).
MIN_WORDS_FOR_LANG_GATE = 1


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    source = unit.data["sentences"]
    raw = parsed.get("sentences")
    if not isinstance(raw, list) or len(raw) != len(source):
        return QaResult(False, "cumle_sayisi_uyusmuyor")

    sentences = [_text(s) for s in raw]
    if any(not s for s in sentences):
        return QaResult(False, "bos_cumle")

    for original, translated in zip(source, sentences):
        if translated.strip().lower() == original.strip().lower():
            return QaResult(False, "ceviri_yapilmamis")
        if len(translated.split()) >= MIN_WORDS_FOR_LANG_GATE and \
                language.looks_english_not_l1(translated, l1):
            return QaResult(False, "l1_ceviri_yapilmamis")

    warnings: list[str] = []
    # UYARI, red degil: ayni cumleyi iki kez uretmek bir bicim hatasi degil,
    # kalite sinyalidir — ceviri yine de kullanilabilir.
    if len({text_qa.normalized_hash_text(s) for s in sentences}) < len(sentences):
        warnings.append("cevrilen_cumleler_ayni")

    return QaResult(True, "; ".join(warnings) or None,
                    payload={"sentences": sentences})
