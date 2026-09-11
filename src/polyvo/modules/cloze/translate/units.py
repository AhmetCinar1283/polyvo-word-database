"""
Ceviri isinin birimleri — YALNIZCA onaylanmis cloze paketleri.

Reddedilmis ya da hic uretilmemis bir paketin cevrilecek cumlesi yoktur.
Sira `cloze/units.py` ile AYNIDIR (`item_id` sirasi): plan ile kosu ayni
birimleri ayni sirada gorsun diye.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.cloze import schema
from polyvo.modules.cloze import units as cloze_units


def _approved_packages(conn) -> dict[str, list[tuple[int, str]]]:
    """`stable_key -> [(seq, cumle)]` — yalnizca ONAYLI paketler, seq sirasinda."""
    rows = conn.execute(
        "SELECT c.stable_key, q.seq, q.sentence"
        " FROM sense_cloze c JOIN sense_cloze_question q"
        "   ON q.sense_id = c.sense_id"
        " WHERE c.status = 'approved' ORDER BY c.stable_key, q.seq").fetchall()
    out: dict[str, list[tuple[int, str]]] = {}
    for stable_key, seq, sentence in rows:
        out.setdefault(stable_key, []).append((seq, sentence))
    return out


def load_units(tag: str, l2: str) -> list[Unit]:
    """Onayli cloze paketi olan anlamlar icin ceviri birimi uretir."""
    base = cloze_units.load_units(tag, l2)
    conn = schema.open_cloze_db()
    try:
        packages = _approved_packages(conn)
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        found = packages.get(unit.key)
        if not found:
            continue                      # paketsiz/reddedilmis anlam: atla
        data = dict(unit.data)
        data["sentences"] = [sentence for _seq, sentence in found]
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
