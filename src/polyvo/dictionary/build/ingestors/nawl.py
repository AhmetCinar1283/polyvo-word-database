"""
NAWL 1.2 — akademik bant (tier 3).

Ayri bir dosya yoktur: NGSL calisma kitabinin `3 - NAWL` bandidir. Bu yuzden
okuyucu `ngsl.py`'den gelir; tekrar yazmak iki kaynagin ayni dosyayi iki
farkli sekilde ayristirmasi demek olurdu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Candidate, FileIngestor
from polyvo.dictionary.build.ingestors.ngsl import NAWL_BAND, iter_bands


@dataclass
class NawlIngestor(FileIngestor):
    """NGSL calisma kitabinin NAWL bandini okur."""
    source_name: str = "nawl"

    def candidates(self) -> Iterable[Candidate]:
        """NAWL bandindaki her lemmadan bir aday uretir."""
        if not self.available():
            return
        for lemma, rank in iter_bands(self.raw_path(), (NAWL_BAND,)):
            yield Candidate(headword=lemma, freq_rank=rank)


INGESTOR = NawlIngestor()
