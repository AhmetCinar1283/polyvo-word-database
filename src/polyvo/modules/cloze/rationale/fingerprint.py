"""
Bayatlik SOZLESMESI'nin deterministik hash'i (V2-IS-5 §12).

`question_sha256`: bir anlamin uc sorusunun cumle+sik metinlerinden — sabit
sira, normalize bosluk. `store.py::load_existing` bunu O ANKI veriden
yeniden hesaplar; tutmayan satir BAYATTIR ve donen sozluge hic konmaz,
`verdict.decide` onu "satir yok" sayar.

`rationale_sha256`: ceviri tarafinin AYNI sozlesmesi — Ingilizce ipucu ve
aciklama metinlerinden. Ingilizce metin degisirse cevirisi bayat olur.
"""

from __future__ import annotations

import hashlib

from polyvo.core.text import qa as text_qa

#: Parcalari ayiran isaret — normalize metnin kendisinde gecmez.
_SEP = "\u241f"


def _digest(parts: list[str]) -> str:
    """Normalize edilmis parcalarin sha256'si, SABIT sirayla birlestirilmis."""
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


def question_sha256(questions: list[dict]) -> str:
    """Bir anlamin uc sorusunun (cumle + siklar) deterministik ozeti.

    `questions` her ogesi `{"seq", "sentence", "options"}` tasir; `options`
    opt_seq sirasindaki metin listesidir."""
    parts: list[str] = []
    for q in sorted(questions, key=lambda item: item["seq"]):
        parts.append(text_qa.normalized_hash_text(q["sentence"]))
        parts.extend(text_qa.normalized_hash_text(o) for o in q["options"])
    return _digest(parts)


def rationale_sha256(hints: list[dict], reasons: list[dict]) -> str:
    """Ingilizce ipucu + aciklama metinlerinin deterministik ozeti.

    `hints` `{"seq", "hint"}`, `reasons` `{"seq", "opt_seq", "reason"}`
    tasir; sira burada SABITLENIR (`seq`/`opt_seq`ye gore), cagiranin hangi
    sirada verdigi onemli degildir."""
    parts = [text_qa.normalized_hash_text(h["hint"])
            for h in sorted(hints, key=lambda h: h["seq"])]
    parts += [text_qa.normalized_hash_text(r["reason"])
             for r in sorted(reasons, key=lambda r: (r["seq"], r["opt_seq"]))]
    return _digest(parts)
