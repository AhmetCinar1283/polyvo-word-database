"""
Ana dil paketinin birimleri — evrendeki HER kelime degil, yalnizca `status=
'approved'` kartla eslesen anlamlar. Kartsiz/onaysiz anlamin cevrilecek bir
seyi yoktur.

Her birimin `data['card']` alanina, promptun BAGLAM olarak kullanacagi
kartin gloss_en/register/ornekleri, (varsa) onayli Ingilizce kullanim notu
ve (varsa) o dilde depoda duran karsilik (`fixed_gloss`) eklenir. Baglam
sorgusu ortak `card_context.py`den gelir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.lexicon_card import card_context, schema
from polyvo.modules.lexicon_card import units as card_units


def load_units(tag: str, l2: str, l1: str) -> list[Unit]:
    """Evrendeki KARTI OLAN anlamlar icin birim uretir; sira kart
    yukleyicisiyle AYNIDIR (`item_id` sirasi)."""
    base = card_units.load_units(tag, l2)
    conn = schema.open_lexicon_db()
    try:
        cards = card_context.approved_cards(conn)
        sense_ids = [c["sense_id"] for c in cards.values()]
        examples = card_context.examples_by_sense(conn, sense_ids)
        notes = card_context.notes_by_sense(conn, sense_ids)
        glosses = card_context.glosses_by_sense(conn, l1)
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        card = cards.get(unit.key)
        if card is None:
            continue                          # kartsiz/onaysiz anlam: atla
        sense_id = card["sense_id"]
        data = dict(unit.data)
        data["card"] = {
            "gloss_en": card["gloss_en"],
            "register": card["register"],
            "examples": examples.get(sense_id, []),
            "usage_note": notes.get(sense_id, {}).get("note", ""),
            "fixed_gloss": glosses.get(sense_id, ""),
        }
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
