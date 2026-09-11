"""
`data/stores/grammar.sqlite` semasi — grammar'in KENDI dosyasi.

Neden ayri dosya: `grammar` yeni bir app'tir; baska bir app'in dosyasina
tablo eklemek iki app'i tek dosyada kilitler. Ayri dosya "yeni tur bir
klasordur" sozunun depo tarafindaki karsiligidir (Is 4'un `cloze.sqlite`si
ile ayni desen).

Dil HER YERDE bir SUTUNDUR: besinci dil satir ekler, tablo/sutun DEGISMEZ.

Durum (status/tier/source/model/prompt_hash) ile ICERIK ayri tablolardadir
(`sense_cloze_translation` + `_sentence` deseni): `sentence_grammar_rule_l1`
ve `grammar_rule_l1` yalnizca ICERIK tasir, durumu `sentence_grammar_
translation`/`grammar_catalog_translation` tasir — boylece bir grubun/kuralin
UC kural notunu/katalog aciklamasini AYNI transaction'da yazip TEK satirdan
"gecti mi" sorulabilir.
"""

from __future__ import annotations

import sqlite3

from polyvo.core import paths, sqlite as sq

GRAMMAR_DB = "grammar.sqlite"

#: `tier`: 0 = insan, 3 = model. Kucuk olan kazanir (`core/jobs/store/policy.py`).
DDL = """
-- Grup basina (bir cumle kumesinin) analiz durumu. Reddedilen grupta kural
-- YAZILMAZ; bu satir yalnizca "burasi denendi ve reddedildi" demek icin durur.
CREATE TABLE IF NOT EXISTS sentence_grammar (
    owner         TEXT    NOT NULL,
    group_key     TEXT    NOT NULL,
    status        TEXT    NOT NULL,
    reject_reason TEXT,
    warnings      TEXT,
    tier          INTEGER NOT NULL,
    source        TEXT    NOT NULL,
    model         TEXT,
    prompt_hash   TEXT,
    source_sha256 TEXT    NOT NULL,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (owner, group_key)
);

-- Cumle basina EN COK MAX_RULES_PER_SENTENCE kural, `rank` SIRALIDIR
-- (1 = tasiyici yapi). `rule_id` KATALOGDAN gelir, KAPALI sozlukten disari
-- CIKMAZ (yazma anindaki kapi `store.py`dedir). `group_key` `ref`in AIT
-- OLDUGU grubu tasir — `translate/units.py`nin `sentence_grammar`a JOIN'i
-- BURADAN yapilir, `ref` metninden ayristirmaya GEREK KALMAZ.
CREATE TABLE IF NOT EXISTS sentence_grammar_rule (
    owner      TEXT    NOT NULL,
    group_key  TEXT    NOT NULL,
    ref        TEXT    NOT NULL,
    rank       INTEGER NOT NULL,
    rule_id    TEXT    NOT NULL,
    trigger    TEXT    NOT NULL,
    note       TEXT    NOT NULL,
    tier       INTEGER NOT NULL,
    source     TEXT    NOT NULL,
    PRIMARY KEY (owner, ref, rank)
);

-- Ceviri paketinin durumu (dil basina, GRUP basina). Ayri kosudur: Ingilizce
-- once uretilir/onaylanir, ceviri sonra.
CREATE TABLE IF NOT EXISTS sentence_grammar_translation (
    owner         TEXT    NOT NULL,
    group_key     TEXT    NOT NULL,
    l1            TEXT    NOT NULL,
    status        TEXT    NOT NULL,
    reject_reason TEXT,
    warnings      TEXT,
    tier          INTEGER NOT NULL,
    source        TEXT    NOT NULL,
    model         TEXT,
    prompt_hash   TEXT,
    note_sha256   TEXT    NOT NULL,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (owner, group_key, l1)
);

-- Cumleye ozel notun cevirisi. `rule_id`/`trigger` BURADA HIC YOK — ikisi de
-- cevrilmez (Is 6 §18).
CREATE TABLE IF NOT EXISTS sentence_grammar_rule_l1 (
    owner  TEXT    NOT NULL,
    ref    TEXT    NOT NULL,
    rank   INTEGER NOT NULL,
    l1     TEXT    NOT NULL,
    note   TEXT    NOT NULL,
    tier   INTEGER NOT NULL,
    source TEXT    NOT NULL,
    PRIMARY KEY (owner, ref, rank, l1)
);

-- Katalog aciklamasinin ceviri DURUMU (kural basina, dil basina). AYRI
-- kosudur, KATALOG BOYUTUNDADIR (yuzler) — kulliyat boyutunda DEGIL.
CREATE TABLE IF NOT EXISTS grammar_catalog_translation (
    rule_id          TEXT    NOT NULL,
    l1               TEXT    NOT NULL,
    status           TEXT    NOT NULL,
    reject_reason    TEXT,
    warnings         TEXT,
    tier             INTEGER NOT NULL,
    source           TEXT    NOT NULL,
    model            TEXT,
    prompt_hash      TEXT,
    catalog_sha256   TEXT    NOT NULL,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_id, l1)
);

-- Katalog aciklamasinin (name/short) cevirisi. `tier=0` ile insan da
-- yazabilir (`assume_known_from`/`trivial` degil, yalnizca metin cevrilir).
CREATE TABLE IF NOT EXISTS grammar_rule_l1 (
    rule_id TEXT    NOT NULL,
    l1      TEXT    NOT NULL,
    name    TEXT    NOT NULL,
    short   TEXT    NOT NULL,
    tier    INTEGER NOT NULL,
    source  TEXT    NOT NULL,
    PRIMARY KEY (rule_id, l1)
);

-- Katalogda KARSILIGI OLMAYAN ama modelin kayda deger bulduğu yapi. Aday
-- SEVK EDILMEZ, GOSTERILMEZ — insan katalogda karsiligini acar (Is 6 §9).
CREATE TABLE IF NOT EXISTS grammar_candidate (
    owner           TEXT    NOT NULL,
    ref             TEXT    NOT NULL,
    seq             INTEGER NOT NULL,
    proposed_name   TEXT    NOT NULL,
    trigger         TEXT    NOT NULL,
    rationale       TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'new',
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (owner, ref, seq)
);
"""


def grammar_db_path() -> str:
    """`data/stores/grammar.sqlite` tam yolu (tag'den BAGIMSIZ — kalicidir)."""
    return paths.store_path(GRAMMAR_DB)


def open_grammar_db(path: str | None = None) -> sqlite3.Connection:
    """Odenmis grammar deposunu acar; tablolarin varligini garanti eder."""
    return sq.connect(path or grammar_db_path(), ddl=DDL, row_factory=True)
