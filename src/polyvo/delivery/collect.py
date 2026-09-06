"""
Sevk edilecek satirlarin TEK toplama yeri. Uc kaynagi birlestirir:

  * `workspace/<tag>/<l2>/universe.sqlite` -> hangi kelimeler bu sevkiyatta
  * `stores/lexicon.sqlite`                -> odenmis icerik (kart, gloss, ornek, IPA)
  * `stores/identity.sqlite`               -> `sense_ordinal` (kimlik alani)

Buradaki hicbir sey KARAR VERMEZ: yalnizca okur ve `Row`lara koyar. Neyin
sevk edilebilir oldugu `gate.py`'nin, nereye yazildigi `materialize.py`'nin isi.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field

from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema

#: Yalnizca bu durumdaki kartlar sevk edilir; digerleri onarim bekler.
SHIPPABLE_STATUS = "approved"


@dataclass
class Row:
    """Sevkiyatin tek bir ogesi — uc dosyaya birden dagilir."""
    item_id: int
    sense_id: int
    stable_key: str
    headword: str
    pos: str
    cefr: str | None
    freq_rank: int | None
    sense_ordinal: int
    status: str
    gloss_en: str | None
    register: str | None
    usage_note: str | None
    ipa: str | None = None
    examples: list[str] = field(default_factory=list)
    gloss_l1: str | None = None
    #: Kapinin baktigi alan: bu satirin METNI hangi kaynaklardan geldi.
    text_sources: set[str] = field(default_factory=set)

    @property
    def examples_json(self) -> str:
        """Ornek cumlelerin sevk bicimi (bos olsa da JSON dizi)."""
        return json.dumps(self.examples, ensure_ascii=False)


@dataclass
class Shipment:
    """Bir `materialize` kosusunun tum girdisi."""
    tag: str
    l2: str
    l1: str | None
    rows: list[Row]
    #: Evrende olup icerigi henuz odenmemis/onaylanmamis kelime sayisi.
    skipped_missing: int = 0
    skipped_not_approved: int = 0


def _open_ro(path: str) -> sqlite3.Connection:
    """Salt-okunur baglanti — sevkiyat kaynaga ASLA yazmaz."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sense_ordinals() -> dict[int, int]:
    """`sense_id -> sense_ordinal`; kimlik dosyasi yoksa bos doner."""
    conn = curriculum_schema.open_identity_db()
    try:
        return {r[0]: r[1] for r in
                conn.execute("SELECT sense_id, sense_ordinal FROM senses")}
    finally:
        conn.close()


def collect(tag: str, l2: str, l1: str | None) -> Shipment:
    """Evren + odenmis depoyu birlestirip sevk adaylarini uretir.

    `item_id` sirasinda doner — sevkiyat dosyalari deterministik olsun diye."""
    universe_path = curriculum_schema.universe_db_path(tag, l2)
    if not os.path.exists(universe_path):
        raise FileNotFoundError(
            f"Evren izdusumu yok: {universe_path}\n"
            f"    Once `polyvo curriculum select --tag {tag} --l2 {l2}` calistirin.")
    lexicon_path = lexicon_schema.lexicon_db_path()
    if not os.path.exists(lexicon_path):
        raise FileNotFoundError(
            f"Odenmis depo yok: {lexicon_path}\n"
            f"    Once `polyvo lexicon-card cards --tag {tag}` calistirin.")

    ordinals = _sense_ordinals()
    cards, glosses, examples, phonetics = _read_lexicon(lexicon_path, l1)

    rows: list[Row] = []
    missing = not_approved = 0
    universe = _open_ro(universe_path)
    try:
        for u in universe.execute(
                "SELECT item_id, sense_id, headword, pos, cefr, freq_rank,"
                " stable_key FROM universe_items ORDER BY item_id"):
            card = cards.get(u["sense_id"])
            if card is None:
                missing += 1
                continue
            if card["status"] != SHIPPABLE_STATUS:
                not_approved += 1
                continue
            row = Row(
                item_id=u["item_id"], sense_id=u["sense_id"],
                stable_key=u["stable_key"], headword=u["headword"],
                pos=u["pos"], cefr=u["cefr"], freq_rank=u["freq_rank"],
                sense_ordinal=ordinals.get(u["sense_id"], 1),
                status=card["status"], gloss_en=card["gloss_en"],
                register=card["register"], usage_note=card["usage_note"],
                ipa=phonetics.get(u["item_id"]),
            )
            row.text_sources.add(card["source"])
            for text, source in examples.get(u["sense_id"], []):
                row.examples.append(text)
                row.text_sources.add(source)
            gloss = glosses.get(u["sense_id"])
            if gloss is not None:
                row.gloss_l1 = gloss[0]
                row.text_sources.add(gloss[1])
            rows.append(row)
    finally:
        universe.close()

    return Shipment(tag=tag, l2=l2, l1=l1, rows=rows,
                    skipped_missing=missing, skipped_not_approved=not_approved)


def _read_lexicon(path: str, l1: str | None):
    """Depoyu dort sozluge okur: kart, L1 gloss, ornekler, IPA."""
    conn = _open_ro(path)
    try:
        cards = {r["sense_id"]: r for r in conn.execute(
            "SELECT sense_id, gloss_en, register, usage_note, status, source"
            " FROM sense_cards")}
        glosses = {}
        if l1:
            glosses = {r["sense_id"]: (r["gloss"], r["source"]) for r in
                       conn.execute("SELECT sense_id, gloss, source FROM"
                                    " sense_gloss_l1 WHERE l1 = ?", (l1,))}
        examples: dict[int, list[tuple[str, str]]] = {}
        for r in conn.execute("SELECT sense_id, text, source FROM sense_examples"
                              " ORDER BY sense_id, seq"):
            examples.setdefault(r["sense_id"], []).append((r["text"], r["source"]))
        # IPA bir OLGUDUR (bkz. dictionary/sources.py) — metin kapisina girmez,
        # bu yuzden kaynagi `text_sources`a EKLENMEZ.
        phonetics = {r["item_id"]: r["ipa"] for r in conn.execute(
            "SELECT item_id, ipa FROM item_phonetics WHERE variant = 'us'")}
        return cards, glosses, examples, phonetics
    finally:
        conn.close()
