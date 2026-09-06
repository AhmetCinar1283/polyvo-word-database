"""
`data/stores/lexicon.sqlite` semasi — ODENMIS KATMAN. Bu dosya asla silinip
yeniden uretilmez; her satiri ya para ya insan emegidir.

MIGRATION-PLAN §5.2 taslagina iki EK var, ikisi de motorun sozlesmesi geregi:
  * `stable_key` — depo kendini anlatsin, `load_existing` TEK sorgu olsun.
  * `status`/`reject_reason` — redo matrisi "kotu satir"i ancak boyle tanir
    (`core/jobs/plan/verdict.py`); statusu olmayan depoda onarim imkansizdir.
"""

from __future__ import annotations

import sqlite3

from polyvo.core import paths, sqlite as sq

LEXICON_DB = "lexicon.sqlite"

#: `tier`: 0 = insan, 1/2 = sozluk tohumu, 3 = model. Kucuk olan kazanir.
DDL = """
CREATE TABLE IF NOT EXISTS sense_cards (
    sense_id       INTEGER PRIMARY KEY,
    item_id        INTEGER NOT NULL,
    stable_key     TEXT    NOT NULL UNIQUE,
    gloss_en       TEXT,
    register       TEXT,
    usage_note     TEXT,
    tier           INTEGER NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'approved',
    reject_reason  TEXT,
    source         TEXT    NOT NULL,
    model          TEXT,
    prompt_hash    TEXT,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sense_gloss_l1 (
    sense_id  INTEGER NOT NULL,
    l1        TEXT    NOT NULL,
    gloss     TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    model     TEXT,
    PRIMARY KEY (sense_id, l1)
);

CREATE TABLE IF NOT EXISTS sense_examples (
    sense_id  INTEGER NOT NULL,
    seq       INTEGER NOT NULL,
    text      TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, seq)
);

-- IPA bir OLGUDUR ve `ipa_dict` (MIT) sevk edilebilir: model uretmez,
-- sozluk tohumu yazar (tier 1).
CREATE TABLE IF NOT EXISTS item_phonetics (
    item_id  INTEGER NOT NULL,
    variant  TEXT    NOT NULL,
    ipa      TEXT    NOT NULL,
    source   TEXT    NOT NULL,
    PRIMARY KEY (item_id, variant)
);

CREATE TABLE IF NOT EXISTS item_forms (
    item_id    INTEGER NOT NULL,
    form_type  TEXT    NOT NULL,
    value      TEXT    NOT NULL,
    PRIMARY KEY (item_id, form_type)
);

CREATE TABLE IF NOT EXISTS item_level (
    item_id    INTEGER PRIMARY KEY,
    cefr       TEXT,
    freq_rank  INTEGER,
    source     TEXT NOT NULL
);
"""


def lexicon_db_path() -> str:
    """`data/stores/lexicon.sqlite` tam yolu (tag'den BAGIMSIZ — kalicidir)."""
    return paths.store_path(LEXICON_DB)


def open_lexicon_db(path: str | None = None) -> sqlite3.Connection:
    """Odenmis depoyu acar; tablolarin varligini garanti eder."""
    return sq.connect(path or lexicon_db_path(), ddl=DDL, row_factory=True)
