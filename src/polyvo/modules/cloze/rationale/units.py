"""
Ipucu/aciklama isinin birimleri — YALNIZCA onayli cloze paketleri.

Reddedilmis ya da hic uretilmemis paketin aciklanacak bir sorusu yoktur.
Sira `cloze/units.py` ile AYNIDIR (`item_id` sirasi): plan ile kosu ayni
birimleri ayni sirada gorsun diye.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.cloze import schema
from polyvo.modules.cloze import units as cloze_units
from polyvo.modules.cloze.rationale import fingerprint


def approved_packages(conn) -> dict[str, list[dict]]:
    """`stable_key -> sorular (siklariyla)` — yalnizca ONAYLI paketler.

    `store.py::load_existing` da AYNI sorguyu kullanir (bayatlik, §12):
    ikisi ayrisirsa "o anki metin" iki farkli sey olurdu."""
    options: dict[tuple[str, int], list[str]] = {}
    for stable_key, seq, text in conn.execute(
            "SELECT c.stable_key, o.seq, o.text"
            " FROM sense_cloze_option o JOIN sense_cloze c"
            "   ON c.sense_id = o.sense_id"
            " WHERE c.status = 'approved'"
            " ORDER BY c.stable_key, o.seq, o.opt_seq"):
        options.setdefault((stable_key, seq), []).append(text)

    out: dict[str, list[dict]] = {}
    for stable_key, seq, sentence, answer in conn.execute(
            "SELECT c.stable_key, q.seq, q.sentence, q.answer"
            " FROM sense_cloze_question q JOIN sense_cloze c"
            "   ON c.sense_id = q.sense_id"
            " WHERE c.status = 'approved' ORDER BY c.stable_key, q.seq"):
        out.setdefault(stable_key, []).append({
            "seq": seq, "sentence": sentence, "answer": answer,
            "options": options.get((stable_key, seq), []),
        })
    return out


def load_units(tag: str, l2: str) -> list[Unit]:
    """Onayli cloze paketi olan anlamlar icin ipucu/aciklama birimi uretir."""
    base = cloze_units.load_units(tag, l2)
    conn = schema.open_cloze_db()
    try:
        packages = approved_packages(conn)
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        questions = packages.get(unit.key)
        if not questions:
            continue                      # paketsiz/reddedilmis anlam: atla
        data = dict(unit.data)
        data["questions"] = questions
        data["question_sha256"] = fingerprint.question_sha256(questions)
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
