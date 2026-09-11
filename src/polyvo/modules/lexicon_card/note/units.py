"""
Kullanim notu isinin birimleri — evrendeki HER kelime degil, yalnizca
`status='approved'` kartla eslesen anlamlar. Kartsiz/onaysiz anlamin notu
olmaz.

Baglam sorgusu ortak `card_context.py`den gelir, burada TEKRARLANMAZ.
"""

from __future__ import annotations

from polyvo.modules.lexicon_card import card_context, schema
from polyvo.modules.lexicon_card import units as card_units
from polyvo.core.jobs.base import Unit


def load_units(tag: str, l2: str) -> list[Unit]:
    """Evrendeki KARTI OLAN anlamlar icin not birimi uretir; sira kart
    yukleyicisiyle AYNIDIR (`item_id` sirasi)."""
    base = card_units.load_units(tag, l2)
    conn = schema.open_lexicon_db()
    try:
        cards = card_context.approved_cards(conn)
        examples = card_context.examples_by_sense(
            conn, [c["sense_id"] for c in cards.values()])
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        card = cards.get(unit.key)
        if card is None:
            continue                          # kartsiz/onaysiz anlam: atla
        data = dict(unit.data)
        data["card"] = {
            "sense_id": card["sense_id"],
            "gloss_en": card["gloss_en"],
            "register": card["register"],
            "examples": examples.get(card["sense_id"], []),
        }
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
