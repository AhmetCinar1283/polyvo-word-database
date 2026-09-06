"""
Havuz — birlestirme boyunca biriken tum gecici veriyi tutan tek nesne.

`_Row` bir `(headword, pos)` adayinin bellekteki hali; `Pool` ise butun
adimlarin (candidates/evidence/resolve/write) OKUYUP YAZDIGI ortak durumdur.
Durumu tek yerde toplamak, "hangi liste nerede guncelleniyor" sorusuna tek
cevap verir — eskiden bu 227 satirlik tek fonksiyonun icinde kapali degisken
olarak dagilmisti.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polyvo.dictionary.build import normalize


@dataclass
class Row:
    """Bir `(headword, pos)` adayinin, tum kaynaklar birlestirildikten
    sonraki hali. `pos` None olabilir (K7); cozumleme `resolve_pos.py`'nin
    isidir."""
    headword: str
    pos: str | None
    tier: int | None = None
    cefr: str | None = None
    freq_rank: int | None = None
    srcs: set[str] = field(default_factory=set)
    pos_source: str | None = None

    def absorb(self, *, tier: int | None, cefr: str | None,
               freq_rank: int | None, source: str | None) -> None:
        """Yeni bir kaynak satirini bu adaya katar (K6: dusuk tier/CEFR kazanir)."""
        self.tier = normalize.merge_tier(self.tier, tier)
        self.cefr = normalize.merge_cefr(self.cefr, cefr)
        if freq_rank is not None:
            self.freq_rank = (freq_rank if self.freq_rank is None
                              else min(self.freq_rank, freq_rank))
        if source:
            self.srcs.add(source)


@dataclass
class Pool:
    """Birlestirmenin ortak durumu: adaylar, kanit, dusen satirlar, sayaçlar."""
    rows: dict[tuple[str, str | None], Row] = field(default_factory=dict)
    unresolved: set[tuple[str, str | None, str, str]] = field(default_factory=set)
    evidence: set[tuple[str, str | None, str, str, str]] = field(default_factory=set)
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    evidence_out_of_universe: int = 0

    def reject(self, headword: str, raw_pos: str | None,
               source: str, reason: str) -> None:
        """Bir satiri SESSIZCE degil, SEBEBIYLE dusurur (`unresolved`'a yazar)."""
        self.unresolved.add((headword, raw_pos, source, reason))

    def universe(self) -> set[str]:
        """Su ana kadar aday olmus tum basliklar — kanit filtrelemek icin sinir."""
        return {head for head, _pos in self.rows}
