"""
Katman 2a'nin sema + dosya yolu dosyasi — iki ayri yerin semasini tasir.

  * `data/stores/identity.sqlite`  -> `items` + `senses` (KUTSAL, GLOBAL,
    asla silinmez — `counters` tablosunu zaten `core/jobs/schema.py` yaratir,
    ayni dosyaya burada iki tablo daha eklenir).
  * `data/workspace/<tag>/<l2>/universe.sqlite` -> `universe_items` (UCUZ,
    tag'e gore, serbestce silinip yeniden uretilir — `items.py` yazar).

Kimligin NEREDE, izdusumun NEREDE yasadigi tek bu dosyada karar verilir;
`items.py` ve `commands/select_command.py` yalnizca bu fonksiyonlari cagirir.
"""

from __future__ import annotations

import json
import os
import sqlite3

from polyvo.core import paths, sqlite as sq
from polyvo.core.jobs import schema as job_schema

#: `identity.sqlite` icindeki kimlik tablolari (MIGRATION-PLAN §5.1).
#: `item_id`/`sense_id` `AUTOINCREMENT` KULLANMAZ — tahsis `core/jobs/identity.py`
#: uzerinden, `counters` sayaciyla yapilir.
ITEMS_SENSES_DDL = """
CREATE TABLE IF NOT EXISTS items (
    item_id     INTEGER PRIMARY KEY,
    l2          TEXT NOT NULL,
    headword    TEXT NOT NULL,
    pos         TEXT NOT NULL,
    stable_key  TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (l2, headword, pos)
);
CREATE INDEX IF NOT EXISTS ix_items_l2 ON items(l2);

CREATE TABLE IF NOT EXISTS senses (
    sense_id       INTEGER PRIMARY KEY,
    item_id        INTEGER NOT NULL REFERENCES items(item_id),
    sense_ordinal  INTEGER NOT NULL,
    is_primary     INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (item_id, sense_ordinal)
);
CREATE INDEX IF NOT EXISTS ix_senses_item ON senses(item_id);
"""

#: `data/workspace/<tag>/<l2>/universe.sqlite` — kimlik tasimaz, sadece
#: kimlik+kaynak alanlarini bir arada TASIR. Bu yuzden hicbir alani KUTSAL
#: degildir; dosya her `select` kosusunda sifirdan yazilir.
UNIVERSE_DDL = """
CREATE TABLE IF NOT EXISTS universe_items (
    item_id     INTEGER PRIMARY KEY,
    sense_id    INTEGER NOT NULL,
    l2          TEXT NOT NULL,
    headword    TEXT NOT NULL,
    pos         TEXT NOT NULL,
    cefr        TEXT,
    freq_rank   INTEGER,
    stable_key  TEXT NOT NULL UNIQUE
);
"""

UNIVERSE_DB = "universe.sqlite"


def open_identity_db() -> sqlite3.Connection:
    """`identity.sqlite`'i acar; `counters` + `items` + `senses` uc tablo da
    garantidir (hangisi eksikse tamamlanir, var olana dokunulmaz)."""
    conn = job_schema.open_identity()
    conn.executescript(ITEMS_SENSES_DDL)
    conn.commit()
    return conn


def universe_db_path(tag: str, l2: str) -> str:
    """`data/workspace/<tag>/<l2>/universe.sqlite` tam yolu."""
    return os.path.join(paths.workspace_dir(tag, l2), UNIVERSE_DB)


def open_universe_db(tag: str, l2: str) -> sqlite3.Connection:
    """Workspace izdusum dosyasini acar; `universe_items` tablosunu garanti eder."""
    return sq.connect(universe_db_path(tag, l2), ddl=UNIVERSE_DDL)


def write_source_config(tag: str, l2: str, payload: dict) -> str:
    """`data/workspace/<tag>/<l2>/source_config.json` — kanonik build kilidi.

    Bir konfig DEGIL, bir OLCUM sonucudur (`core/config.py` docstring'i):
    bu izdusumun HANGI build satir sayilariyla kilitlendigini soyler."""
    path = paths.source_config_path(tag, l2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"tag": tag, "l2": l2, **payload}, fh, ensure_ascii=False,
                   indent=2, sort_keys=False)
        fh.write("\n")
    return path
