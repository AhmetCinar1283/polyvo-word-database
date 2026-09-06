"""TOEIC Service List 1.1 — sinav bandi (tier 3). Sutunlar: Word, TSL Rank, SFI, U."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Candidate, FileIngestor


@dataclass
class TslIngestor(FileIngestor):
    """TSL 1.1 CSV'sini okur."""
    source_name: str = "tsl"

    def candidates(self) -> Iterable[Candidate]:
        """Her satirdan bir aday uretir; POS tasimaz."""
        if not self.available():
            return
        with open(self.raw_path(), newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                word = (row.get("Word") or "").strip()
                if not word:
                    continue
                rank = row.get("TSL Rank")
                yield Candidate(headword=word,
                                freq_rank=int(rank) if rank and rank.isdigit() else None)


INGESTOR = TslIngestor()
