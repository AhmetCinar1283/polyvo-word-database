"""
Sevkiyat dosyalarinin semasi + adlari (MIGRATION-PLAN §5.4).

Uc dosya duzeni KORUNUR — bolme dile goredir, tabloya gore degil:
  * `core.db`      dilden BAGIMSIZ kimlik ve seviye (item_id, CEFR, frekans)
  * `en.db`        L2 metni (baslik, EN gloss, IPA, ornek cumleler)
  * `i18n_<l1>.db` L1 metni (TR karsilik) — yeni dil = yeni DOSYA, yeni sutun degil

`meta` tablosu her dosyada bulunur ve LISANS ATIFINI tasir: atif verinin
yaninda gider, belgede degil.

ZAMAN DAMGASI YOK: dosyalar deterministik olsun diye uretim zamani yalnizca
`_dist_meta.json`'a yazilir (bkz. `snapshot.py`).
"""

from __future__ import annotations

import os

from polyvo.core import paths

CORE_DB = "core.db"


def l2_db(l2: str) -> str:
    """L2 metin dosyasinin adi, orn. `en.db`."""
    return f"{l2}.db"


def l1_db(l1: str) -> str:
    """L1 metin dosyasinin adi, orn. `i18n_tr.db`."""
    return f"i18n_{l1}.db"


def dist_path(tag: str, l2: str, filename: str) -> str:
    """`data/dist/<tag>/<l2>/<filename>` tam yolu."""
    return os.path.join(paths.dist_dir(tag, l2), filename)


def filenames(l2: str, l1: str | None) -> list[str]:
    """Bir sevkiyatin uretecegi dosya adlari (L1 yoksa iki dosya)."""
    names = [CORE_DB, l2_db(l2)]
    if l1:
        names.append(l1_db(l1))
    return names


#: Her dosyada bulunan atif/kimlik tablosu — anahtar/deger, sirali yazilir.
META_DDL = """
CREATE TABLE meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""

CORE_DDL = META_DDL + """
CREATE TABLE items (
    item_id        INTEGER PRIMARY KEY,
    stable_key     TEXT    NOT NULL UNIQUE,
    part_of_speech TEXT    NOT NULL,
    -- NULL OLABILIR: CEFR bir IPUCUDUR, evrenin her kelimesinde yoktur.
    cefr           TEXT,
    frequency_rank INTEGER,
    sense_id       INTEGER NOT NULL UNIQUE,
    sense_ordinal  INTEGER NOT NULL
);
CREATE INDEX ix_items_rank ON items(frequency_rank);
"""

L2_DDL = META_DDL + """
CREATE TABLE item_text (
    item_id       INTEGER PRIMARY KEY,
    headword      TEXT NOT NULL,
    gloss         TEXT NOT NULL,
    -- NULL OLABILIR: IPA sozluk tohumundan gelir, her kelimede bulunmaz.
    ipa           TEXT,
    register      TEXT,
    usage_note    TEXT,
    examples_json TEXT NOT NULL      -- JSON dizi; ornek yoksa "[]"
);
"""

L1_DDL = META_DDL + """
CREATE TABLE item_gloss (
    item_id  INTEGER PRIMARY KEY,
    gloss    TEXT NOT NULL
);
"""
