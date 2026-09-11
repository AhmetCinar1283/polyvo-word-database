"""
`data/stores/cloze.sqlite` semasi — ODENMIS KATMAN, kendi dosyasi.

Neden `lexicon.sqlite`in icinde degil: cloze ayri bir app'tir; baska bir
app'in dosyasina tablo eklemek iki app'i tek dosyada kilitler. Ayri dosya,
"yeni tur bir klasordur" sozunun depo tarafindaki karsiligidir.

UC SORU TEK PAKETTIR: birlikte uretilir, birlikte onaylanir. `status` bu
yuzden paketin (`sense_cloze`) uzerindedir — kardes durum tablosu gerekmez
(Is 3'un `sense_translation` deseni).

SIKLAR CEVRILMEZ, dolayisiyla `sense_cloze_option` DILE BAGLI DEGILDIR:
besinci bir dil eklemek yalnizca satir ekler, TABLO/SUTUN degistirmez.
"""

from __future__ import annotations

import sqlite3

from polyvo.core import paths, sqlite as sq

CLOZE_DB = "cloze.sqlite"

#: `tier`: 0 = insan, 3 = model. Kucuk olan kazanir (`core/jobs/store/policy.py`).
DDL = """
-- Anlam basina UC sorunun paket durumu. Reddedilen pakette ICERIK yazilmaz;
-- bu satir yalnizca "burasi denendi ve reddedildi" demek icin durur.
CREATE TABLE IF NOT EXISTS sense_cloze (
    sense_id      INTEGER PRIMARY KEY,
    stable_key    TEXT    NOT NULL,
    status        TEXT    NOT NULL,
    reject_reason TEXT,
    warnings      TEXT,
    tier          INTEGER NOT NULL,
    source        TEXT    NOT NULL,
    model         TEXT,
    prompt_hash   TEXT,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tek soru: bosluklu INGILIZCE cumle + dogru cevap. `seq` zorluk sirasidir
-- (1 kolay, 2 orta, 3 zor) ve `difficulty` modelden DEGIL bizden gelir.
CREATE TABLE IF NOT EXISTS sense_cloze_question (
    sense_id   INTEGER NOT NULL,
    seq        INTEGER NOT NULL,
    difficulty TEXT    NOT NULL,
    sentence   TEXT    NOT NULL,
    answer     TEXT    NOT NULL,
    tier       INTEGER NOT NULL,
    source     TEXT    NOT NULL,
    PRIMARY KEY (sense_id, seq)
);

-- Dort sik: biri dogru cevap (`is_answer=1`), ucu celdirici. INGILIZCEDIR
-- ve cevrilmez — bu bir Ingilizce alistirmasidir.
CREATE TABLE IF NOT EXISTS sense_cloze_option (
    sense_id  INTEGER NOT NULL,
    seq       INTEGER NOT NULL,
    opt_seq   INTEGER NOT NULL,
    text      TEXT    NOT NULL,
    is_answer INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sense_id, seq, opt_seq)
);

-- Ceviri paketinin durumu (dil basina). Ayri kosudur: cloze once Ingilizce
-- uretilir ve onaylanir, ceviri sonra — boylece besinci dil cloze'u yeniden
-- odettirmez.
CREATE TABLE IF NOT EXISTS sense_cloze_translation (
    sense_id      INTEGER NOT NULL,
    l1            TEXT    NOT NULL,
    status        TEXT    NOT NULL,
    reject_reason TEXT,
    warnings      TEXT,
    tier          INTEGER NOT NULL,
    source        TEXT    NOT NULL,
    model         TEXT,
    prompt_hash   TEXT,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sense_id, l1)
);

-- Cevrilen sey CUMLEDIR, siklar degil: boslugu DOLDURULMUS tam cumlenin
-- cevirisi. Ne zaman gosterilecegi uygulamanin karari.
CREATE TABLE IF NOT EXISTS sense_cloze_translation_sentence (
    sense_id  INTEGER NOT NULL,
    l1        TEXT    NOT NULL,
    seq       INTEGER NOT NULL,
    sentence  TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, l1, seq)
);

-- Is 5: ipucu + sik basina aciklama, cloze'un USTUNE (yukaridaki uc tabloya
-- HIC dokunmadan). `question_sha256` bir SOZLESMEDIR: soru insan tarafindan
-- duzeltilirse ya da yeniden uretilirse bu satir BAYATLASIR
-- (`rationale/store.py::load_existing` o anki soru/sik metninden hash'i
-- yeniden hesaplayip karsilastirir).
CREATE TABLE IF NOT EXISTS sense_cloze_rationale (
    sense_id        INTEGER PRIMARY KEY,
    stable_key      TEXT    NOT NULL,
    status          TEXT    NOT NULL,
    reject_reason   TEXT,
    warnings        TEXT,
    tier            INTEGER NOT NULL,
    source          TEXT    NOT NULL,
    model           TEXT,
    prompt_hash     TEXT,
    question_sha256 TEXT    NOT NULL,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Soru basina TEK ipucu. `hint_seq` bugun HER ZAMAN 1'dir; ikinci kademe
-- (daha acik) bir ipucu ileride SATIR ekler, sutun/tablo degismez.
CREATE TABLE IF NOT EXISTS sense_cloze_hint (
    sense_id  INTEGER NOT NULL,
    seq       INTEGER NOT NULL,
    hint_seq  INTEGER NOT NULL,
    hint      TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, seq, hint_seq)
);

-- Sik basina TEK aciklama (dogru cevap dahil dordu de). Anahtar
-- `sense_cloze_option` ile BIREBIR AYNIDIR: "her cevap icin aciklama" tam
-- anlamiyla sikka baglidir.
CREATE TABLE IF NOT EXISTS sense_cloze_option_reason (
    sense_id  INTEGER NOT NULL,
    seq       INTEGER NOT NULL,
    opt_seq   INTEGER NOT NULL,
    reason    TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, seq, opt_seq)
);

-- Ipucu/aciklama paketinin ceviri durumu (dil basina). AYRI KOSUDUR: mevcut
-- `cloze translate` (cumle cevirisi) ile BIRLESTIRILMEZ, cumle cevirileri
-- icin zaten odendi. `rationale_sha256` ayni bayatlik sozlesmesini
-- Ingilizce ipucu/aciklama metni icin tekrarlar.
CREATE TABLE IF NOT EXISTS sense_cloze_rationale_translation (
    sense_id          INTEGER NOT NULL,
    l1                TEXT    NOT NULL,
    status            TEXT    NOT NULL,
    reject_reason     TEXT,
    warnings          TEXT,
    tier              INTEGER NOT NULL,
    source            TEXT    NOT NULL,
    model             TEXT,
    prompt_hash       TEXT,
    rationale_sha256  TEXT    NOT NULL,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sense_id, l1)
);

-- Cevrilmis ipucu. Besinci dil = yeni SATIR, sema degismez.
CREATE TABLE IF NOT EXISTS sense_cloze_hint_l1 (
    sense_id  INTEGER NOT NULL,
    l1        TEXT    NOT NULL,
    seq       INTEGER NOT NULL,
    hint_seq  INTEGER NOT NULL,
    hint      TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, l1, seq, hint_seq)
);

-- Cevrilmis sik aciklamasi. Siklarin KENDISI hic cevrilmez (Is 4 §14);
-- aciklamanin icinde sikkin Ingilizce kelimesi BILEREK kalir.
CREATE TABLE IF NOT EXISTS sense_cloze_option_reason_l1 (
    sense_id  INTEGER NOT NULL,
    l1        TEXT    NOT NULL,
    seq       INTEGER NOT NULL,
    opt_seq   INTEGER NOT NULL,
    reason    TEXT    NOT NULL,
    tier      INTEGER NOT NULL,
    source    TEXT    NOT NULL,
    PRIMARY KEY (sense_id, l1, seq, opt_seq)
);
"""


def cloze_db_path() -> str:
    """`data/stores/cloze.sqlite` tam yolu (tag'den BAGIMSIZ — kalicidir)."""
    return paths.store_path(CLOZE_DB)


def open_cloze_db(path: str | None = None) -> sqlite3.Connection:
    """Odenmis cloze deposunu acar; tablolarin varligini garanti eder."""
    return sq.connect(path or cloze_db_path(), ddl=DDL, row_factory=True)
