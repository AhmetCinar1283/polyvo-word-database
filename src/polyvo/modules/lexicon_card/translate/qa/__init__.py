"""
Tek paketin (karsilik + ceviri) icerik kapisi — ORKESTRASYON.

Sira: karsilik (`gloss.py`) -> ceviri (`entry.py`) -> terim tutarliligi
(`consistency.py`, yalnizca uyari). Ilk RED kazanir, kalan kapi cagrilmaz;
UYARILAR hepsinden toplanir. Paketin TEK karari vardir — bir parca
reddedilirse hicbir icerik yazilmaz.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.lexicon_card.translate.qa import consistency, entry, gloss


def _warnings(result: QaResult) -> list[str]:
    """Onayli sonucun `reason`indaki uyarilari listeye acar."""
    return [w for w in (result.reason or "").split("; ") if w]


def run(parsed: dict | None, unit: Unit, l1: str) -> QaResult:
    """Paketi dogrular; gecerse depoya yazilacak birlesik yuku uretir."""
    warnings: list[str] = []
    payload: dict = {}
    for part in (gloss, entry):
        result = part.run(parsed, unit, l1)
        if not result.ok:
            return result
        warnings.extend(_warnings(result))
        payload.update(result.payload)

    warnings.extend(consistency.check(payload["gloss_l1"], payload["examples"], l1))
    return QaResult(True, "; ".join(warnings) or None, payload=payload)
