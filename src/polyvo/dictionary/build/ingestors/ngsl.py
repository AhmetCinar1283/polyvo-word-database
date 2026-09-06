"""
NGSL 1.01 — evrenin cekirdegi (tier 1).

Calisma kitabi TEK sayfadan olusur ve 80.831 satir tasir; bunlarin yalnizca
3.807'si bir listeye aittir (`Wordlist` sutunu). Geri kalan 77.023 satir
frekans kuyrugudur ve OGRETIM LISTESI DEGILDIR — evrene alinmaz
(docs/SOURCES.md §2.1: uyelik kurali "bir ogretim listesinde geciyor olmak").

Ayni kitap NAWL'i da tasir; onu `nawl.py` bu modulun okuyucusuyla okur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from polyvo.dictionary.build.ingestors.base import Candidate, FileIngestor

#: `Wordlist` sutunundaki bant adlari. NGSL ile "Sup" ayni basamaktir:
#: Supplementary sayilar/aylar/gunler gibi cekirdek girdilerdir (47 satir).
NGSL_BANDS = ("1 - NGSL", "2 - Sup")
NAWL_BAND = "3 - NAWL"


def iter_bands(path: str, bands: tuple[str, ...]) -> Iterator[tuple[str, int | None]]:
    """`(lemma, rank)` — yalnizca istenen bantlardan. Tembel okur."""
    import openpyxl  # yalnizca bu kaynak icin gerekli; import yerel kalsin

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        for row in ws.iter_rows(min_row=2, values_only=True):
            lemma, wordlist, rank = row[0], row[1], row[2]
            if wordlist not in bands or not lemma:
                continue
            yield str(lemma), int(rank) if isinstance(rank, (int, float)) else None
    finally:
        wb.close()


@dataclass
class NgslIngestor(FileIngestor):
    """NGSL calisma kitabinin NGSL+Sup bantlarini okur."""
    source_name: str = "ngsl"

    def candidates(self) -> Iterable[Candidate]:
        """NGSL+Sup bantlarindaki her lemmadan bir aday uretir."""
        if not self.available():
            return
        for lemma, rank in iter_bands(self.raw_path(), NGSL_BANDS):
            # POS tasimaz (K7): `raw_pos` None kalir, cozumleme merge'in isi.
            yield Candidate(headword=lemma, freq_rank=rank)


INGESTOR = NgslIngestor()
