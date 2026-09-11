"""
Ipucu + aciklama cevabinin icerik kapisi — ORKESTRASYON.

Sira: bicim -> ipucu -> aciklama -> seviye. Ilk RED kazanir ve kalan kapilar
cagrilmaz. Cloze `qa/__init__.py` ile AYNI desen (V2-IS-5 §14). `level`
sona konur: hicbir sey reddetmez, yalnizca uyari toplar.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.cloze.rationale.qa import format as format_check
from polyvo.modules.cloze.rationale.qa import hint, level, reason


def run(parsed: dict | None, unit: Unit) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir."""
    reject, questions = format_check.check(parsed, unit)
    if reject:
        return QaResult(False, reject)

    warnings: list[str] = []
    for check in (hint, reason, level):
        reject, found = check.check(questions, unit)
        if reject:
            return QaResult(False, reject)
        warnings.extend(found)

    payload = {
        "hints": [{"seq": q["seq"], "hint": q["hint"]} for q in questions],
        "reasons": [
            {"seq": q["seq"], "opt_seq": r["opt_seq"], "reason": r["reason"]}
            for q in questions for r in q["reasons"]
        ],
    }
    return QaResult(True, "; ".join(warnings) or None, payload=payload)
