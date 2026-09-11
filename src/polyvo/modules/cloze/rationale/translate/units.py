"""
Ceviri isinin birimleri — YALNIZCA onayli ipucu/aciklama paketleri.

Reddedilmis ya da hic uretilmemis paketin cevrilecek bir metni yoktur. Sira
`rationale/units.py` ile AYNIDIR (`stable_key` sirasi).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.rationale import fingerprint
from polyvo.modules.cloze.rationale import units as rationale_units


def approved_rationales(conn) -> dict[str, dict]:
    """`stable_key -> {"hints": [...], "reasons": [...]}` — yalnizca ONAYLI.

    `store.py::load_existing` da AYNI sorguyu kullanir (bayatlik, §12).
    `reasons` ogeleri sikkin Ingilizce METNINI de tasir (`text`) — §16'nin
    "cevirmeden once bilinen sik kelimesini cikar" kurali bunu gerektirir."""
    hints: dict[str, list[dict]] = {}
    for stable_key, seq, hint in conn.execute(
            "SELECT c.stable_key, h.seq, h.hint"
            " FROM sense_cloze_hint h JOIN sense_cloze_rationale c"
            "   ON c.sense_id = h.sense_id"
            " WHERE c.status = 'approved' AND h.hint_seq = 1"
            " ORDER BY c.stable_key, h.seq"):
        hints.setdefault(stable_key, []).append({"seq": seq, "hint": hint})

    reasons: dict[str, list[dict]] = {}
    for stable_key, seq, opt_seq, reason_text, option_text in conn.execute(
            "SELECT c.stable_key, r.seq, r.opt_seq, r.reason, o.text"
            " FROM sense_cloze_option_reason r"
            " JOIN sense_cloze_rationale c ON c.sense_id = r.sense_id"
            " JOIN sense_cloze_option o ON o.sense_id = r.sense_id"
            "   AND o.seq = r.seq AND o.opt_seq = r.opt_seq"
            " WHERE c.status = 'approved'"
            " ORDER BY c.stable_key, r.seq, r.opt_seq"):
        reasons.setdefault(stable_key, []).append({
            "seq": seq, "opt_seq": opt_seq, "reason": reason_text,
            "text": option_text})

    return {key: {"hints": hints.get(key, []), "reasons": reasons.get(key, [])}
            for key in hints}


def load_units(tag: str, l2: str) -> list[Unit]:
    """Onayli ipucu/aciklama paketi olan anlamlar icin ceviri birimi uretir."""
    base = rationale_units.load_units(tag, l2)
    conn = schema.open_cloze_db()
    try:
        rationales = approved_rationales(conn)
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        found = rationales.get(unit.key)
        if not found:
            continue                      # paketsiz/reddedilmis anlam: atla
        data = dict(unit.data)
        data["hints"] = found["hints"]
        data["reasons"] = found["reasons"]
        data["rationale_sha256"] = fingerprint.rationale_sha256(
            found["hints"], found["reasons"])
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
