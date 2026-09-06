"""
CEFR-J Vocabulary Profile 1.5 — A1–B2 omurgasi (tier 2).

Iki tuhafligi var, ikisi de olculdu (2026-09-05):

  * `headword` bir kelime degil, EGIK CIZGIYLE AYRILMIS YAZIM VARYANTLARI
    olabilir: `analyze/analyse`, `airplane/aeroplane` (167 satir). Ilk varyant
    basa alinir, digerleri `form` kaniti olur — iki yazim ayni ogretim birimi.
  * POS sozlugu genistir: `be-verb`, `infinitive-to`, `modal auxiliary`...
    Cevirisi `normalize.py`'de; burada ham etiket AYNEN aktarilir.
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
class CefrjIngestor(FileIngestor):
    """CEFR-J CSV'sini okur."""
    source_name: str = "cefrj"

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
        """Ilkten sonraki her yazim varyantini `form` kaniti olarak verir."""
        if not self.available():
            return
        for row in _rows(self.raw_path()):
            parts = normalize.split_variants(row.get("headword") or "")
            for alt in parts[1:]:
                yield Evidence(headword=parts[0], kind="form", payload=alt,
                               raw_pos=(row.get("pos") or "").strip() or None)


INGESTOR = CefrjIngestor()
