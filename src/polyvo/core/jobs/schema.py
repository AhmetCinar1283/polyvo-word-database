"""
Motorun sahip oldugu depo dosyalari ve DDL'leri — TEK yerde. Motor yalnizca
IKI dosyanin sahibidir: `identity.sqlite` (`counters`, monotonik kimlik) ve
`job_attempts.sqlite` (`job_attempts`, INSERT-ONLY gunluk). Uretilen
ICERIGIN sekli (gloss, ornek) motorun isi degil — onu her modul kendi
deposunda tanimlar; motor icerige degil YAZMA KAPISINA sahiptir.

`identity.sqlite` `curriculum`un `items`/`senses` tablolarini da tasir; bu
DDL yalnizca `counters`i yaratir, digerlerine dokunmaz.
"""

from __future__ import annotations

import sqlite3

from polyvo.core import paths, sqlite as sq

IDENTITY_DB = "identity.sqlite"
ATTEMPTS_DB = "job_attempts.sqlite"

#: Monotonik kimlik sayaclari. `AUTOINCREMENT` KULLANILMAZ (§6.2): tahsis
#: acikca gorunur ve yeniden uretilebilir olmali.
COUNTERS_DDL = """
    CREATE TABLE IF NOT EXISTS counters (
        name     TEXT PRIMARY KEY,
        next_id  INTEGER NOT NULL
    );
"""

#: Deneme gunlugu: her LLM denemesi (reddedilenler dahil) buraya bir kez
#: yazilir ve BIR DAHA GUNCELLENMEZ. UPDATE olsaydi bir onarim kosusu, neyin
#: nicin reddedildigini anlatan tek kaydi uzerine yazardi.
ATTEMPTS_DDL = """
    CREATE TABLE IF NOT EXISTS job_attempts (
        attempt_row_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id          TEXT NOT NULL,
        family          TEXT NOT NULL,
        kind            TEXT NOT NULL,
        l2              TEXT NOT NULL,
        l1              TEXT NOT NULL DEFAULT '',
        variant         TEXT NOT NULL DEFAULT '',
        stable_key      TEXT NOT NULL,
        model_label     TEXT,
        prompt_version  TEXT,
        attempt         INTEGER NOT NULL,
        from_cache      INTEGER NOT NULL DEFAULT 0,
        status          TEXT NOT NULL,
        reject_reason   TEXT,
        raw_response    TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_attempts_key
        ON job_attempts (family, kind, l2, stable_key);
    CREATE INDEX IF NOT EXISTS ix_attempts_run
        ON job_attempts (run_id);
"""


def identity_path() -> str:
    """`data/stores/identity.sqlite` tam yolu."""
    return paths.store_path(IDENTITY_DB)


def attempts_path() -> str:
    """`data/stores/job_attempts.sqlite` tam yolu."""
    return paths.store_path(ATTEMPTS_DB)


def open_identity(path: str | None = None) -> sqlite3.Connection:
    """Kimlik deposunu acar; `counters` tablosunu garanti eder."""
    return sq.connect(path or identity_path(), ddl=COUNTERS_DDL, row_factory=True)


def open_attempts(path: str | None = None) -> sqlite3.Connection:
    """Deneme gunlugunu acar; `job_attempts` tablosunu garanti eder."""
    return sq.connect(path or attempts_path(), ddl=ATTEMPTS_DDL, row_factory=True)
