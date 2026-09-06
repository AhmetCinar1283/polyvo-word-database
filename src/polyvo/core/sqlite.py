"""
SQLite erisiminin TEK kapisi: pragma'lar, guvenli kopya, guvenli olcum.

1. `busy_timeout` 30 sn — dosya kilidi paralel yazan iki komutta aninda
   `database is locked` yerine bekler.
2. Kopyalama `backup` API ile — WAL'daki commit edilmis ama checkpoint
   edilmemis satirlari `shutil.copy` sessizce dusurur.
3. `row_counts` hicbir zaman istisna firlatmaz — bozuk/eksik dosyada `None`.
"""

from __future__ import annotations

import os
import sqlite3

BUSY_TIMEOUT_MS = 30_000


def apply_pragmas(conn: sqlite3.Connection, *, foreign_keys: bool = True) -> None:
    """WAL + busy_timeout + foreign_keys pragmalarini uygular."""
    cur = conn.cursor()
    if foreign_keys:
        cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")


def connect(path: str, *, ddl: str | None = None, row_factory: bool = False,
            foreign_keys: bool = True) -> sqlite3.Connection:
    """Dizini olusturur, baglanir, pragma'lari uygular, verilen DDL'i kosar."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    if row_factory:
        conn.row_factory = sqlite3.Row
    apply_pragmas(conn, foreign_keys=foreign_keys)
    if ddl:
        conn.executescript(ddl)
        conn.commit()
    return conn


def backup_copy(src_path: str, dst_path: str) -> None:
    """WAL-guvenli kopya (backup API, shutil.copy degil)."""
    os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
    src = sqlite3.connect(src_path)
    try:
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def is_sqlite(path: str) -> bool:
    """Dosya gercekten SQLite mi -- baglanmadan, imzasina bakarak."""
    try:
        with open(path, "rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def table_names(conn: sqlite3.Connection) -> list[str]:
    """Dosyadaki kullanici tablolarinin adlari."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in rows]


def row_counts(path: str) -> dict[str, int] | None:
    """Dosyadaki her tablonun satir sayisi; okunamazsa `None` (istisna firlatmaz)."""
    if not os.path.exists(path) or not is_sqlite(path):
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        counts: dict[str, int] = {}
        for name in table_names(conn):
            try:
                counts[name] = conn.execute(
                    f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except sqlite3.Error:
                counts[name] = -1      # tablo okunamadi; kosuyu dusurme
        return counts
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def dir_row_counts(directory: str, suffixes: tuple[str, ...] = (".db", ".sqlite")) -> dict:
    """Dizindeki (kok seviye) veritabani dosyalarinin tablo/satir dokumu."""
    out: dict[str, dict] = {}
    if not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        if not name.endswith(suffixes):
            continue
        counts = row_counts(os.path.join(directory, name))
        if counts is not None:
            out[name] = counts
    return out
