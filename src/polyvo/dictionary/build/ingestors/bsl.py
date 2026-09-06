"""Business Service List 1.01 — is ingilizcesi bandi (tier 3). Sutunlar: Word, BSL Rank, SFI, U, D, F."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Candidate, FileIngestor


@dataclass
class BslIngestor(FileIngestor):
    """BSL 1.01 CSV'sini okur."""
    source_name: str = "bsl"

    def candidates(self) -> Iterable[Candidate]:
        """Her satirdan bir aday uretir; POS tasimaz."""
        if not self.available():
            return
        with open(self.raw_path(), newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                word = (row.get("Word") or "").strip()
                if not word:
                    continue
                rank = row.get("BSL Rank")
                yield Candidate(headword=word,
                                freq_rank=int(rank) if rank and rank.isdigit() else None)


INGESTOR = BslIngestor()
