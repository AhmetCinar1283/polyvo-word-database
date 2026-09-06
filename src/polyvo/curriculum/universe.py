"""
Evren secimi + kapi — `data/builds/<tag>/01_lexicon/`daki adaylardan, Adim 5+'in
uzerinde calisacagi sabit kelime evrenini kurar.

KAPI (§6 kural 1): `gate()` hicbir sey basip sessizce devam etmez; evren bossa
ya da icinde yinelenen bir (headword, pos) varsa `UniverseError` firlatir.
Cagiran komut (curriculum/commands/select_command.py) bunu YAKALAMAZ — exit
kodu dogal olarak 1 olur ve hicbir dosya yazilmis olmaz.

Bu dosya SIFIR LLM cagirir (katman 2a, MIGRATION-PLAN §1). Yalnizca ucuz
katmani (`candidates`) okur, kimlige DOKUNMAZ — kimlik tahsisi `items.py`'nin isi.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.core import sqlite as sq


class UniverseError(Exception):
    """Evren kurulamadi — kaynak eksik/bozuk ya da secim bos/yinelenen."""


@dataclass(frozen=True)
class Candidate:
    """`lexicon.sqlite/candidates`'tan okunan tek bir aday, degismez."""
    headword: str
    pos: str
    cefr: str | None
    freq_rank: int | None


@dataclass
class UniverseSelection:
    """`select_universe()`un sonucu: neyin evrene girdigi + neyin neden disarida kaldigi."""
    kept: list[Candidate]
    excluded_pos_missing: int
    excluded_over_target: int

    @property
    def size(self) -> int:
        """Evrene giren aday sayisi."""
        return len(self.kept)


def read_candidates(db_path: str) -> tuple[list[Candidate], int]:
    """`(pos'lu adaylar, pos'suz elenen sayisi)` doner.

    POS'suz satirlar evrene giremez: `stable_key` ("en:bank:noun") POS'suz
    kurulamaz (K1). Bu bir sessiz eleme degildir — sayisi cagirana geri doner
    ve komut ciktisinda raporlanir."""
    if not sq.is_sqlite(db_path):
        raise UniverseError(
            f"Kaynak lexicon gecerli bir SQLite dosyasi degil: {db_path}\n"
            f"    Once: polyvo dictionary build")
    conn = sq.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT headword, pos, cefr, freq_rank FROM candidates").fetchall()
    finally:
        conn.close()
    kept = [Candidate(headword=r[0], pos=r[1], cefr=r[2], freq_rank=r[3])
            for r in rows if r[1] is not None]
    missing = sum(1 for r in rows if r[1] is None)
    return kept, missing


def _sort_key(c: Candidate):
    """Frekans sirasi once (bilinmeyen en sona), sonra alfabetik — DETERMINIZM
    icin: ayni girdi HER ZAMAN ayni sirayi uretmeli (kimlik tahsisi bu siraya
    dayanir, bkz. items.py)."""
    return (c.freq_rank is None, c.freq_rank if c.freq_rank is not None else 0,
            c.headword, c.pos)


def select_universe(candidates: list[Candidate], *, target_size: int,
                     pos_missing_count: int = 0) -> UniverseSelection:
    """Adaylari sirala, ilk `target_size` kadarini evrene al.

    SAF fonksiyon — veritabanina dokunmaz, testte kurulum yapmadan cagirilir."""
    if target_size < 1:
        raise ValueError("target_size >= 1 olmali")
    ordered = sorted(candidates, key=_sort_key)
    kept = ordered[:target_size]
    over = max(0, len(ordered) - target_size)
    return UniverseSelection(kept=kept, excluded_pos_missing=pos_missing_count,
                              excluded_over_target=over)


def gate(selection: UniverseSelection) -> None:
    """Yazmadan ONCE calisan kapi. Ihlalde `UniverseError` — cagiran hicbir
    dosya yazmadan durur (§6 kural 1: uyarip exit 0 donen kapi, kapi degildir)."""
    if selection.size == 0:
        raise UniverseError("Secilen evren BOS — hicbir dosya yazilmadi.")
    seen: set[tuple[str, str]] = set()
    for c in selection.kept:
        key = (c.headword, c.pos)
        if key in seen:
            raise UniverseError(
                f"Evren icinde yinelenen (headword, pos): {key} — "
                f"hicbir dosya yazilmadi.")
        seen.add(key)
