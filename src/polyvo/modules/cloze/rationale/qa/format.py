"""
BICIM kapisi + SIK ESLEMESI — sayilabilir olan her sey. Hepsi REDDEDER.

Sik eslemesi METINLE yapilir (`text_qa.fold_for_match`): model aciklamayi
sikkin METNIYLE etiketler, `opt_seq`i BIZ atariz (kaynaktaki sira). Var
olmayan bir sik metnine baglanmis aciklama bir bicim hatasidir (V2-IS-5 §14
"eslesmeyen = red").

Bu kapi cevabi ayni zamanda NORMALLESTIRIR: donen her soru gercek sik
METNINI tasir (modelin dondurdugu degil), sonraki kapilar temiz bir yapiyla
calisir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze.difficulty import OPTION_COUNT, QUESTION_COUNT


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def check(parsed: dict | None, unit: Unit) -> tuple[str | None, list[dict]]:
    """(red_sebebi, normallestirilmis_sorular) doner.

    Donen her soru: `{"seq", "hint", "sentence", "answer", "options",
    "reasons": [{"opt_seq", "text", "reason"}, ...]}`."""
    if not isinstance(parsed, dict):
        return "cevap_json_degil", []

    raw = parsed.get("questions")
    if not isinstance(raw, list) or len(raw) != QUESTION_COUNT:
        return "soru_sayisi_uc_degil", []

    sources = sorted(unit.data["questions"], key=lambda q: q["seq"])
    if len(sources) != QUESTION_COUNT:
        return "kaynak_soru_sayisi_uc_degil", []

    out: list[dict] = []
    for source, item in zip(sources, raw):
        if not isinstance(item, dict):
            return "soru_nesne_degil", []

        hint = _text(item.get("hint"))
        if not hint:
            return "ipucu_bos", []

        raw_reasons = item.get("reasons")
        if not isinstance(raw_reasons, list) or len(raw_reasons) != OPTION_COUNT:
            return "aciklama_sayisi_dort_degil", []

        by_fold = {text_qa.fold_for_match(o): (i + 1, o)
                  for i, o in enumerate(source["options"])}
        if len(by_fold) != OPTION_COUNT:
            return "kaynak_siklar_katlaninca_ayirt_edilemiyor", []

        reasons: list[dict] = []
        seen: set[int] = set()
        for r in raw_reasons:
            if not isinstance(r, dict):
                return "aciklama_nesne_degil", []
            option_text = _text(r.get("option"))
            reason_text = _text(r.get("reason"))
            if not option_text or not reason_text:
                return "aciklama_alani_bos", []
            found = by_fold.get(text_qa.fold_for_match(option_text))
            if found is None:
                return "aciklama_olmayan_sikka_bagli", []
            opt_seq, real_text = found
            if opt_seq in seen:
                return "aciklama_ayni_sikka_iki_kez_bagli", []
            seen.add(opt_seq)
            reasons.append({"opt_seq": opt_seq, "text": real_text,
                            "reason": reason_text})

        out.append({"seq": source["seq"], "hint": hint,
                    "sentence": source["sentence"], "answer": source["answer"],
                    "options": source["options"], "reasons": reasons})

    return None, out
