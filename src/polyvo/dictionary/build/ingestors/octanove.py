"""
Octanove Vocabulary Profile C1/C2 1.0 — ust bant (tier 3).

Sutunlar: headword, pos, CEFR, notes.

  * `headword` CEFR-J'deki gibi egik cizgili varyant tasiyabilir (50 satir);
    bolme kurali ortaktir, `normalize.split_variants`.
  * `notes` bir MINI TANIMDIR (`cast/noun` -> "plaster cast, mold") ve ayni
    `(headword, pos)` cifti farkli notlarla tekrar edebilir — yani bu sutun
    ANLAM AYRIMI tasir. Kanit olarak saklanir; ogrenciye gitmez.
  * Bilinen tek kusuru bir POS yazim hatasidir (`vern`, 1 satir); duzeltme
    `normalize.POS_TYPO_FIXES` icinde ACIKCA beyan edilir.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build import normalize
from polyvo.dictionary.build.ingestors.base import Candidate, Evidence, FileIngestor


def _rows(path: str) -> Iterable[dict[str, str]]:
    """CSV'yi sozluk satirlari olarak okur."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        yield from csv.DictReader(fh)


@dataclass
class OctanoveIngestor(FileIngestor):
    """Octanove C1/C2 CSV'sini okur."""
    source_name: str = "octanove"

    def candidates(self) -> Iterable[Candidate]:
        """Ilk yazim varyantindan bir aday uretir; POS ve CEFR ham gecer."""
        if not self.available():
            return
        for row in _rows(self.raw_path()):
            parts = normalize.split_variants(row.get("headword") or "")
            if not parts:
                continue
            yield Candidate(headword=parts[0],
                            raw_pos=(row.get("pos") or "").strip() or None,
                            cefr=(row.get("CEFR") or "").strip() or None)

    def evidence(self) -> Iterable[Evidence]:
        """Yazim varyantlarini `form`, `notes` sutununu `definition` kaniti verir."""
        if not self.available():
            return
        for row in _rows(self.raw_path()):
            parts = normalize.split_variants(row.get("headword") or "")
            if not parts:
                continue
            raw_pos = (row.get("pos") or "").strip() or None
            for alt in parts[1:]:
                yield Evidence(parts[0], kind="form", payload=alt, raw_pos=raw_pos)
            note = (row.get("notes") or "").strip()
            if note:
                yield Evidence(parts[0], kind="definition", payload=note,
                               raw_pos=raw_pos)


INGESTOR = OctanoveIngestor()
