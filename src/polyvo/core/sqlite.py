"""
SQLite erisiminin TEK kapisi: pragma'lar, guvenli kopya, guvenli olcum.

Uc kural burada merkezilesti; ucu de eski repoda ayri ayri kanamis seylerdir.

1. `busy_timeout` SIFIR DEGIL (30 sn). SQLite'in yazma kilidi TABLO basina
   degil DOSYA basinadir. Ayni dosyaya yazan iki komut paralel kostugunda
   varsayilan 0 ile ikincisi BEKLEMEDEN `database is locked` ile olur
   (olculdu: kilit 2 sn tutuldu -> 0 ms'de crash, 0 satir; 30 sn ile 2,1 sn
   bekleyip yazdi). Pragma'lar tek yerde oldugu icin bu her dosya icin gecerli.

2. KOPYALAMA `shutil.copy` DEGIL, backup API. Depolar WAL modunda calisir;
   `-wal` yan dosyasi olmadan alinan ham kopya, commit edilmis ama henuz
   checkpoint edilmemis satirlari DUSURUR — yani sessizce eksik bir yedek.

3. OLCUM (`row_counts`) HER ZAMAN KORUMALI. `sqlite3.connect()` actigi dosyayi
   dogrulamaz; bozuk ya da SQLite olmayan bir dosya sorunsuz "acilir", hata ilk
   sorguda gelir. Korumasiz bir istatistik yardimcisi, saatler suren bir kosuyu
   TUM IS BITTIKTEN SONRA dusurur.
"""

from __future__ import annotations

import os
import sqlite3

BUSY_TIMEOUT_MS = 30_000


def apply_pragmas(conn: sqlite3.Connection, *, foreign_keys: bool = True) -> None:
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
    """WAL-guvenli kopya (bkz. modul docstring'i, kural 2)."""
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
    """Dosyanin gercekten bir SQLite veritabani olup olmadigi — baglanmadan,
    imzasina bakarak. `connect` bunu SOYLEMEZ (kural 3)."""
    try:
        with open(path, "rb") as f:
            return f.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in rows]


def row_counts(path: str) -> dict[str, int] | None:
    """Dosyadaki her tablonun satir sayisi. Dosya okunamaz/bozuksa `None`
    doner — ASLA istisna firlatmaz (kural 3)."""
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
    """Bir dizindeki (yalnizca kok seviyesindeki) veritabani dosyalarinin
    tablo/satir dokumu — asama meta dosyalarinin `row_counts` alani icin."""
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
