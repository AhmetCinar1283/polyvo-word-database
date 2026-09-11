"""
Paketin CEVIRI parcasinin (tanim + not + ornekler) kapisi — eski
`translate/qa.py`, kapilari degismeden tasindi. HEPSI YA DA HIC (Is 3 madde 7).

Bu, Is 2b'nin duzelttigi hatayla KARISTIRILMAMALI: oradaki hata odenmis bir
INGILIZCE karti BASKA bir dilin kalitesi yuzunden cope atmakti. Burada
paketin tamami AYNI isin, AYNI dilin urunu — eksik alan bir bicim hatasidir,
yeniden denenir; kart tarafina HICBIR KOSULDA dokunulmaz.

Dil isaretci kapisi (`l1_language`) burada UZUN metinde calisir (tanim tam
bir cumledir) — kisa cevaptaki ayirt edememe sorunu (`l1_form.py`) burada
gecerli degildir, esik 1 kelimeye ayarlanir.

"Model cevirmedi" karari iki katmanlidir ve AGIRLIK GARANTI EDILEBILEN
katmandadir: kaynak Ingilizce metinle karsilastirma (`_unchanged`, hem tanim
hem HER ornek icin). Dil isaretcisi ikinci katmandir, sezgiseldir ve
2026-09-07'de daraltilmistir — bkz. `core/text/qa.py::english_marker_hits`.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.lexicon_card import l1_language

#: Tanim bu uzunlugu asarsa aciklamaya donmustur, sozluk glossu degildir.
MAX_DEFINITION_CHARS = 300
#: Dil isaretci kapisi tanim/ornek gibi UZUN cevapta 1 kelimeden itibaren
#: gecerlidir — kisa karsilikta ayirt edememe sorunu burada yoktur.
MIN_WORDS_FOR_LANG_GATE = 1


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _examples(value) -> list[str] | None:
    """Ornek listesini dogrular; liste degilse `None`."""
    if not isinstance(value, list):
        return None
    return [_text(v) for v in value]


def _unchanged(answer: str, source: str) -> bool:
    """Cevap KAYNAK Ingilizce metnin aynisi mi? Bu GARANTI EDILEBILIR bir
    hatadir (model cevirmemis, metni geri dondurmus) ve dil isaretcisi
    sezgisinden bagimsiz calisir — kapinin asil yuku burada tasinir."""
    return text_qa.normalized_hash_text(answer) == text_qa.normalized_hash_text(source)


def _check_language(text: str, l1: str) -> str | None:
    """Metin cevrilmemis (Ingilizce kalmis) mi? Uzun metinde esik 1 kelime."""
    if len(text.split()) < MIN_WORDS_FOR_LANG_GATE:
        return None
    if l1_language.looks_english_not_l1(text, l1):
        return "l1_ceviri_yapilmamis"
    return None


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    card = unit.data["card"]
    source_examples = card["examples"]
    source_note = card.get("usage_note") or ""

    definition = _text(parsed.get("definition"))
    if not definition:
        return QaResult(False, "tanim_bos")
    if len(definition) > MAX_DEFINITION_CHARS:
        return QaResult(False, "tanim_cok_uzun")
    if _unchanged(definition, card["gloss_en"]):
        return QaResult(False, "ceviri_yapilmamis")
    lang_code = _check_language(definition, l1)
    if lang_code:
        return QaResult(False, lang_code)

    examples = _examples(parsed.get("examples"))
    if examples is None or len(examples) != len(source_examples):
        return QaResult(False, "ornek_sayisi_uyusmuyor")
    if any(not ex for ex in examples):
        return QaResult(False, "bos_ornek_cumle")
    for ex, source_ex in zip(examples, source_examples):
        if _unchanged(ex, source_ex):
            return QaResult(False, "ceviri_yapilmamis")
        lang_code = _check_language(ex, l1)
        if lang_code:
            return QaResult(False, lang_code)

    note = _text(parsed.get("usage_note"))
    if source_note and not note:
        return QaResult(False, "ceviri_notu_eksik")
    if note:
        if note.strip().lower() == source_note.strip().lower():
            return QaResult(False, "not_cevrilmemis")
        lang_code = _check_language(note, l1)
        if lang_code:
            return QaResult(False, lang_code)

    warnings: list[str] = []
    # UYARI, red degil: cekim/turetme tam cozulemedigi icin garanti edilemez.
    if len({text_qa.normalized_hash_text(ex) for ex in examples}) < len(examples):
        warnings.append("ornekler_ayni")

    return QaResult(True, "; ".join(warnings) or None, payload={
        "definition": definition,
        "usage_note": note,
        "examples": examples,
    })
