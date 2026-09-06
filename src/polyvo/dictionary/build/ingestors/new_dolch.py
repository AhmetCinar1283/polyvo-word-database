"""
New Dolch List 1.0 — en temel gorsel kelimeler (tier 1).

Dosyanin BASLIK SATIRI YOKTUR ve satir uzunlugu degiskendir: ilk sutun lemma,
kalani o lemmanin cekimli bicimleridir (`able,abler,ablest,ables,abled,...`).
Cekimler evrene AYRI KELIME olarak girmez — `form` kaniti olarak saklanir;
`ables` bir ogretim birimi degil, `able`in bir bicimidir.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Candidate, Evidence, FileIngestor


def _rows(path: str) -> Iterable[list[str]]:
    """Basliksiz CSV'yi satir satir okur; bos hucreleri atar."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh):
            cells = [c.strip() for c in row if c and c.strip()]
            if cells:
                yield cells


@dataclass
class NewDolchIngestor(FileIngestor):
    """New Dolch CSV'sini okur."""
    source_name: str = "new_dolch"

    def candidates(self) -> Iterable[Candidate]:
        """Her satirin ilk hucresinden (lemma) bir aday uretir."""
        if not self.available():
            return
        for rank, cells in enumerate(_rows(self.raw_path()), start=1):
            yield Candidate(headword=cells[0], freq_rank=rank)

    def evidence(self) -> Iterable[Evidence]:
        """Lemmanin cekimli bicimlerini `form` kaniti olarak verir."""
        if not self.available():
            return
        for cells in _rows(self.raw_path()):
            for form in cells[1:]:
                if form != cells[0]:
                    yield Evidence(headword=cells[0], kind="form", payload=form)


INGESTOR = NewDolchIngestor()
