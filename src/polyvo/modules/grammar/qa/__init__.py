"""
Grammar cevabinin icerik kapisi — ORKESTRASYON.

Sira: bicim -> trigger -> katalog -> asikarlik -> seviye/siralama. Ilk RED
kazanir ve kalan kapilar cagrilmaz. UYARILAR hepsinden toplanir ve onayli
cevapta da tasinir (`QaResult.reason` onayda da dolu olabilir).

RED / UYARI ayrimi Is 6'nin en onemli karari: garanti EDILEBILEN sey
reddeder, edilemeyen UYARIR (§6.7). Neyin neden uyari oldugu ilgili
dosyanin docstring'inde yazilidir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import QaResult, Unit
from polyvo.modules.grammar.qa import catalog, level, shape, trigger, trivial


def _candidates_payload(sentences: list[dict]) -> list[dict]:
    """`grammar_candidate` icin duz liste — GRUP REDDEDILSE BILE tasinir:
    aday havuzu modelin `rules` alaninda hata yapip yapmadigindan BAGIMSIZ,
    kendi basina degerlidir (§9)."""
    return [
        {"ref": s["ref"], "seq": seq, **c}
        for s in sentences
        for seq, c in enumerate(s["candidates"], start=1)
    ]


def run(parsed: dict | None, unit: Unit) -> QaResult:
    """Cevabi dogrular; gecerse depoya yazilacak yuku de uretir.

    Adaylar BICIM asamasindan hemen sonra cikarilir ve red YOLUNDA da
    payload'a konur: `store.py` boylece "kurallar reddedildi ama adaylar
    gecerli" durumunu ayirt edebilir (§9 kapisinin testle olculdugu yer)."""
    reject, sentences = shape.check(parsed, unit)
    if reject:
        return QaResult(False, reject)

    candidates = _candidates_payload(sentences)
    refs = [s["ref"] for s in sentences]

    warnings: list[str] = []
    for check in (trigger, catalog, trivial):
        reject, found = check.check(sentences, unit)
        if reject:
            return QaResult(False, reject,
                            payload={"candidates": candidates, "refs": refs})
        warnings.extend(found)

    # Seviye/siralama HICBIR ZAMAN reddetmez; en sonda cagrilir.
    _reject, level_warnings = level.check(sentences, unit)
    warnings.extend(level_warnings)

    rules = [
        {"ref": s["ref"], "rank": r["rank"], "rule_id": r["rule_id"],
         "trigger": r["trigger"], "note": r["note"]}
        for s in sentences for r in s["rules"]
    ]
    return QaResult(True, "; ".join(warnings) or None,
                    payload={"rules": rules, "candidates": candidates,
                             "refs": refs})
