"""
Cloze cevabinin icerik kapisi — ORKESTRASYON.

Sira: bicim -> bosluk -> celdirici -> seviye -> tekduzelik. Ilk RED kazanir
ve kalan kapilar cagrilmaz (reddedilmis bir pakette digerlerini olcmek
anlamsizdir). UYARILAR ise hepsinden toplanir ve onayli cevapta da tasinir —
`QaResult.reason` onayda da dolu olabilir (`core/jobs/base.py`).

RED / UYARI ayrimi bu isin en onemli karari: garanti EDILEBILEN sey reddeder,
edilemeyen UYARIR (§6.7). Neyin neden uyari oldugu ilgili dosyanin
docstring'inde yazilidir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.cloze.qa import blank, distractor, level, shape, variety


def run(parsed: dict | None, unit: Unit) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    reject, questions = shape.check(parsed)
    if reject:
        return QaResult(False, reject)

    warnings: list[str] = []
    for check in (blank, distractor, level, variety):
        reject, found = check.check(questions, unit)
        if reject:
            return QaResult(False, reject)
        warnings.extend(found)

    return QaResult(True, "; ".join(warnings) or None,
                    payload={"questions": questions})
