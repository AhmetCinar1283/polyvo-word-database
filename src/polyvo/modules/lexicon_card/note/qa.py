"""
Kullanim notu cevabinin icerik kapisi.

REDDEDEN kontroller garanti edilebilir olanlardir: alan eksik/gecersiz
`reason`, not `gloss_en`in kopyasi ya da yeniden ifadesi. Notun "gercekten
gerekli" olup olmadigi garanti EDILEMEZ (§6.7) — bu yuzden REDDETMEZ, uyarir.

EN ONEMLI KURAL: `reason == "none"` + BOS not, GECERLI ONAYLI cevaptir. Modele
"istersen doldur" demek olculdu ve 957'de 4 verdi (eski `usage_note` alani);
bu kapi sebep-once modelini garanti eder.
"""

from __future__ import annotations

import re

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.lexicon_card.note.prompt import REASONS

#: Not bu uzunlugu asarsa aciklamaya donmustur, kisa not degil.
MAX_NOTE_CHARS = 220

#: Not ile tanim arasindaki kelime ortusme orani bunu asarsa "yeniden ifade"
#: sayilir — olculebilir tek esik.
COPY_OVERLAP_RATIO = 0.8

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _token_set(text: str) -> set[str]:
    """Karsilastirma icin kucuk-harfli kelime kumesi."""
    return {w.lower() for w in _WORD_RE.findall(text)}


def _looks_like_definition_copy(note: str, gloss_en: str) -> bool:
    """Not, tanimin neredeyse ayni kelimelerinin yeniden dizilimi mi?
    Olculebilir: kelime kumesi ortusmesi COPY_OVERLAP_RATIO'yu asarsa evet."""
    note_tokens, def_tokens = _token_set(note), _token_set(gloss_en)
    if not note_tokens or not def_tokens:
        return False
    overlap = len(note_tokens & def_tokens)
    return overlap / len(note_tokens) >= COPY_OVERLAP_RATIO


def run(parsed: dict | None, unit: Unit) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    if not isinstance(parsed, dict):
        return QaResult(False, "cevap_json_degil")

    reason = _text(parsed.get("reason")).lower()
    note = _text(parsed.get("usage_note"))
    warnings: list[str] = []

    if reason not in REASONS:
        warnings.append("not_sebebi_taninmadi_none_yazildi")
        reason = "none"

    if reason == "none":
        if note:
            # Sebep yok dedi ama not yazdi — bicim hatasi, para kaybi degil:
            # boslugu KORU, uyariyla isaretle.
            warnings.append("sebep_none_ama_not_dolu_bosaltildi")
            note = ""
        return QaResult(True, "; ".join(warnings) or None,
                        payload={"reason": reason, "note": ""})

    if not note:
        # Sebep var ama not bos — bicim hatasi: sebebi none'a dusur, notu bos birak.
        warnings.append("sebep_var_ama_not_bos_none_yazildi")
        return QaResult(True, "; ".join(warnings) or None,
                        payload={"reason": "none", "note": ""})

    if len(note) > MAX_NOTE_CHARS:
        return QaResult(False, "not_cok_uzun")

    gloss_en = unit.data["card"]["gloss_en"]
    if note.strip().lower() == gloss_en.strip().lower():
        return QaResult(False, "not_tanimin_kopyasi")
    if _looks_like_definition_copy(note, gloss_en):
        return QaResult(False, "not_tanimin_yeniden_ifadesi")

    # UYARI, red degil: "gercekten gerekli mi" garanti edilemez (§6.7).
    warnings.append("not_gerekliligi_dogrulanamadi")

    return QaResult(True, "; ".join(warnings) or None,
                    payload={"reason": reason, "note": note})
