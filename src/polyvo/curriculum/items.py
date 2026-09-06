"""
Kimlik tahsisi + workspace izdusumu — evrendeki her adaya kalici bir
item_id/sense_id verir ve `data/workspace/<tag>/<l2>/universe.sqlite`'a yazar.

IDEMPOTENT KURAL (Adim 4 kabul testi, MIGRATION-PLAN §7): `data/stores/
identity.sqlite` asla silinmez (GLOBAL katman, `core/paths.py`). Bu yuzden
ayni (l2, headword, pos) icin ikinci kez cagrildiginda YENI kimlik almaz,
VAR OLANI kullanir — `workspace/` tamamen silinip yeniden uretilse bile
item_id/sense_id BIREBIR AYNI cikar. Sifirdan (identity.sqlite de silinmis)
bir kosuda da ayni sonuc cikar, cunku `universe.py` adaylari HER ZAMAN ayni
sirada (`_sort_key`) getirir ve tahsis o siraya gore, tek transaction icinde
yapilir.

Bu dosya sadece BIR anlam (sense_ordinal=1, is_primary=1) acar; anlam bolme
(birden fazla sense) LLM isidir ve v2 kapsamindadir (MIGRATION-PLAN §7 Ertelendi).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from polyvo.core.jobs import identity
from polyvo.curriculum import schema
from polyvo.curriculum.universe import Candidate


@dataclass(frozen=True)
class ProjectedItem:
    """Kimlik + kaynak alanlari birlesmis, workspace'e yazilacak tek satir."""
    item_id: int
    sense_id: int
    l2: str
    headword: str
    pos: str
    cefr: str | None
    freq_rank: int | None
    stable_key: str


def stable_key(l2: str, headword: str, pos: str) -> str:
    """`"en:bank:noun"` bicimindeki degismez anahtar (MIGRATION-PLAN §5.1)."""
    return f"{l2}:{headword}:{pos}"


def _ensure_item(conn: sqlite3.Connection, l2: str, headword: str, pos: str) -> int:
    """Var olan (l2, headword, pos) satirinin kimligini doner; yoksa YENI tahsis eder."""
    row = conn.execute(
        "SELECT item_id FROM items WHERE l2 = ? AND headword = ? AND pos = ?",
        (l2, headword, pos)).fetchone()
    if row is not None:
        return int(row[0])
    item_id = identity.allocate_one(conn, "items")
    conn.execute(
        "INSERT INTO items (item_id, l2, headword, pos, stable_key) VALUES (?,?,?,?,?)",
        (item_id, l2, headword, pos, stable_key(l2, headword, pos)))
    return item_id


def _ensure_primary_sense(conn: sqlite3.Connection, item_id: int) -> int:
    """Var olan birincil anlamin kimligini doner; yoksa YENI tahsis eder."""
    row = conn.execute(
        "SELECT sense_id FROM senses WHERE item_id = ? AND sense_ordinal = 1",
        (item_id,)).fetchone()
    if row is not None:
        return int(row[0])
    sense_id = identity.allocate_one(conn, "senses")
    conn.execute(
        "INSERT INTO senses (sense_id, item_id, sense_ordinal, is_primary) "
        "VALUES (?,?,1,1)", (sense_id, item_id))
    return sense_id


def assign_identities(conn: sqlite3.Connection, l2: str,
                       candidates: list[Candidate]) -> list[ProjectedItem]:
    """Sirali listedeki her adaya item_id + birincil sense_id verir.

    TEK transaction icinde: kosu ortasinda kesilirse yari tahsis kalmaz
    (identity.py'nin `allocate` docstring'indeki ayni gerekce)."""
    out = []
    with conn:
        for c in candidates:
            item_id = _ensure_item(conn, l2, c.headword, c.pos)
            sense_id = _ensure_primary_sense(conn, item_id)
            out.append(ProjectedItem(
                item_id=item_id, sense_id=sense_id, l2=l2, headword=c.headword,
                pos=c.pos, cefr=c.cefr, freq_rank=c.freq_rank,
                stable_key=stable_key(l2, c.headword, c.pos)))
    return out


def write_workspace(tag: str, l2: str, projected: list[ProjectedItem]) -> str:
    """`universe.sqlite`'i SIFIRDAN yazar (`build/write_lexicon.py` ile ayni
    desen: her kosuda once silinir, sonra yeniden yaratilir). UCUZ katman —
    kimlik burada DOGMAZ, sadece tasinir."""
    db_path = schema.universe_db_path(tag, l2)
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = schema.open_universe_db(tag, l2)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO universe_items (item_id, sense_id, l2, headword,"
                " pos, cefr, freq_rank, stable_key) VALUES (?,?,?,?,?,?,?,?)",
                [(p.item_id, p.sense_id, p.l2, p.headword, p.pos, p.cefr,
                  p.freq_rank, p.stable_key)
                 for p in sorted(projected, key=lambda p: p.item_id)])
    finally:
        conn.close()
    return db_path
