"""
`data/builds/<tag>/01_lexicon/lexicon.sqlite` semasi — UCUZ KATMAN, tamamen
silinip yeniden uretilebilir, hicbir kimlik/odenmis karar barindirmaz.

`candidates` evrene aday (pos NULL olabilir, K7) · `evidence` LLM'e kanit
(ogrenciye dogrudan gitmez) · `unresolved` dusen her satir SEBEBIYLE ·
`source_meta` hangi kaynak kac satir verdi.
"""

from __future__ import annotations

DDL = """
CREATE TABLE IF NOT EXISTS candidates (
    headword      TEXT    NOT NULL,
    pos           TEXT,               -- NULL olabilir (K7): POS'suz liste girdisi
    tier          INTEGER,            -- evren merdiveni; NULL = evren uretmeyen kaynak
    cefr          TEXT,               -- K6 ile birlestirilmis nihai deger
    freq_rank     INTEGER,            -- kaynak sirasi (mutlak degil, gostergesel)
    is_multiword  INTEGER NOT NULL DEFAULT 0,   -- K5
    sources       TEXT    NOT NULL,   -- virgulle ayrilmis kaynak adlari
    pos_source    TEXT,               -- POS'u hangi kaynak cozdu
    PRIMARY KEY (headword, pos)
);

-- Ayni headword'un POS'suz satiri ile POS'lu satirlari birlikte yasayabilir;
-- cozumleme adimi POS'suz olani siler. Bu indeks o adimi ucuzlatir.
CREATE INDEX IF NOT EXISTS idx_candidates_headword ON candidates(headword);
CREATE INDEX IF NOT EXISTS idx_candidates_tier     ON candidates(tier);

CREATE TABLE IF NOT EXISTS evidence (
    headword    TEXT NOT NULL,
    pos         TEXT,
    kind        TEXT NOT NULL,   -- definition | example | synonym | antonym | ipa | form
    payload     TEXT NOT NULL,
    source      TEXT NOT NULL,
    PRIMARY KEY (headword, pos, kind, source, payload)
);

CREATE INDEX IF NOT EXISTS idx_evidence_headword ON evidence(headword);

CREATE TABLE IF NOT EXISTS unresolved (
    headword  TEXT NOT NULL,
    raw_pos   TEXT,
    source    TEXT NOT NULL,
    reason    TEXT NOT NULL,
    PRIMARY KEY (headword, raw_pos, source, reason)
);

CREATE TABLE IF NOT EXISTS source_meta (
    source        TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    license       TEXT NOT NULL,
    attribution   TEXT NOT NULL,
    shippable     INTEGER NOT NULL,
    tier          INTEGER,
    candidates_in INTEGER NOT NULL DEFAULT 0,
    evidence_in   INTEGER NOT NULL DEFAULT 0
);
"""
