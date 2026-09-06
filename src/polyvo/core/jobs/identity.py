"""
Monotonik kimlik tahsisi — `counters` tablosu uzerinden, `AUTOINCREMENT`siz.
`AUTOINCREMENT` tabloya baglidir; tablo bosalirsa kimlikler BASA DONER ve
ayni sayi baska bir kayda gider. Sayac ayri satir: veri silinse de geri gitmez.

`floor` (orn. `MAX(id)`) yalnizca sayac hic yoksa, ILK kurulusta okunur.
Bu modul kimligin NEYE verildigini BILMEZ (`items`/`senses` curriculum'un
tablolaridir) — alt katman ust katmani import edemez.
"""

from __future__ import annotations

import sqlite3


def _read(conn: sqlite3.Connection, name: str) -> int | None:
    """Sayacin mevcut degeri; satir yoksa `None`."""
    row = conn.execute("SELECT next_id FROM counters WHERE name = ?", (name,)).fetchone()
    return int(row[0]) if row is not None else None


def current(conn: sqlite3.Connection, name: str, *, floor: int = 0) -> int:
    """Bir sonraki tahsis edilecek kimlik — HICBIR SEY TUKETMEDEN."""
    value = _read(conn, name)
    return max(floor + 1, 1) if value is None else value


def ensure(conn: sqlite3.Connection, name: str, *, floor: int = 0) -> int:
    """Sayaci yoksa `floor + 1`'den baslatir; mevcut degerini doner.

    `floor` mevcut en buyuk kimliktir (`MAX(id)`). Bir sayaci bilerek geri
    almanin yolu yok: `floor` yalnizca ILK kurulusta okunur."""
    value = _read(conn, name)
    if value is not None:
        return value
    start = max(floor + 1, 1)
    conn.execute("INSERT INTO counters (name, next_id) VALUES (?, ?)", (name, start))
    return start


def allocate(conn: sqlite3.Connection, name: str, count: int = 1,
             *, floor: int = 0) -> range:
    """`count` adet ardisik kimlik ayirir ve araligini doner.

    Blok halinde ayirmak sart: tek tek `UPDATE` etmek hem yavastir hem de
    kosunun ortasinda kesilirse yarim tahsis birakir. `range` doner ki
    cagiran taraf sayilari sirayla kullansin."""
    if count < 1:
        raise ValueError("count >= 1 olmali")
    start = ensure(conn, name, floor=floor)
    conn.execute("UPDATE counters SET next_id = ? WHERE name = ?", (start + count, name))
    return range(start, start + count)


def allocate_one(conn: sqlite3.Connection, name: str, *, floor: int = 0) -> int:
    """Tek bir kimlik ayirir — `allocate(...)[0]`in okunakli hali."""
    return allocate(conn, name, 1, floor=floor)[0]
