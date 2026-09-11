"""
`lexicon_card`in ILAN EDILMIS okuma yuzeyi — baska bir app'in bu app'ten
gorebilecegi TEK sey.

Neden var: cloze gibi yeni bir icerik turunun odenmis karta (headword, pos,
gloss_en, ornekler, CEFR) ihtiyaci gercektir; ama `lexicon_card`in icine
dagilmis importlar iki app'i tek dosyada kilitler. Bu yuzden disariya TEK
yuzey acilir ve `tests/test_layering.py` bunu OLCER.

SALT OKUNUR: burada yazma API'si YOKTUR ve olmayacaktir. Bir app baska bir
app'in deposuna yazamaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.modules.lexicon_card import card_context, schema
from polyvo.modules.lexicon_card import units as card_units


@dataclass(frozen=True)
class SenseView:
    """Disaridan gorunen anlam: kimlik + odenmis kartin icerigi.

    Donduruldugu anda kopyadir (`frozen`) — cagiran bunu degistirerek depoya
    dokunamaz."""

    stable_key: str
    sense_id: int
    item_id: int
    headword: str
    pos: str
    cefr: str | None
    gloss_en: str
    register: str | None
    examples: tuple[str, ...]


def approved_senses(tag: str, l2: str) -> list[SenseView]:
    """Evrendeki ONAYLI kartla eslesen anlamlar, `item_id` sirasinda.

    Kartsiz ya da onaylanmamis anlam listeye HIC girmez: onun uzerine icerik
    uretilemez."""
    base = card_units.load_units(tag, l2)
    conn = schema.open_lexicon_db()
    try:
        cards = card_context.approved_cards(conn)
        examples = card_context.examples_by_sense(
            conn, [c["sense_id"] for c in cards.values()])
    finally:
        conn.close()

    views: list[SenseView] = []
    for unit in base:
        card = cards.get(unit.key)
        if card is None:
            continue
        views.append(SenseView(
            stable_key=unit.key,
            sense_id=card["sense_id"],
            item_id=unit.data["item_id"],
            headword=unit.data["headword"],
            pos=unit.data["pos"],
            cefr=unit.data["cefr"],
            gloss_en=card["gloss_en"],
            register=card["register"],
            examples=tuple(examples.get(card["sense_id"], [])),
        ))
    return views
