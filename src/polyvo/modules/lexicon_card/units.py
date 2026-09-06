"""
Birim yukleyici — `workspace/<tag>/<l2>/universe.sqlite`'i `Unit` listesine
cevirir. Evreni SECMEZ, kimlik URETMEZ: ikisi de Adim 4'un isi (`curriculum/`).

Sira `item_id`e gore SABITTIR — plan ile kosu ayni birimleri ayni sirada
gorsun diye (`core/jobs/base.py::Job.load_units` sozlesmesi).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.curriculum import schema as curriculum_schema


def load_units(tag: str, l2: str) -> list[Unit]:
    """Evren izdusumundeki her kelime icin bir `Unit` uretir."""
    conn = curriculum_schema.open_universe_db(tag, l2)
    try:
        rows = conn.execute(
            "SELECT item_id, sense_id, headword, pos, cefr, freq_rank, stable_key"
            "  FROM universe_items ORDER BY item_id"
        ).fetchall()
    finally:
        conn.close()

    return [
        Unit(
            key=stable_key,
            name=f"{headword} ({pos})",
            data={"item_id": item_id, "sense_id": sense_id, "headword": headword,
                  "pos": pos, "cefr": cefr, "freq_rank": freq_rank},
        )
        for item_id, sense_id, headword, pos, cefr, freq_rank, stable_key in rows
    ]
