"""
Bir gramer kuralinin veri bicimi + id gecerliligi.

Id BICIMI SABITTIR: `EN.<ALAN>.<KURAL>` — buyuk harf, nokta ayracli, uc parca,
`[A-Z0-9_]` disinda karakter yok. `EN` L2 dil koduDUR: baska bir L2 eklenirse
ONEK degisir, bicim degismez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: `<ALAN>` KAPALI listeden gelir; gelisigüzel buyumez, gerekirse ELLE eklenir.
AREAS: frozenset[str] = frozenset({
    "TENSE", "ASPECT", "MODAL", "VOICE", "INF", "GER", "PART", "COND",
    "CLAUSE", "REL", "QUES", "NEG", "ART", "NOUN", "PRON", "ADJ", "ADV",
    "COMP", "PREP", "CONJ", "QUANT", "ORDER", "PHRASAL", "COLLOC", "DISC",
})

_ID_RE = re.compile(r"^EN\.([A-Z0-9_]+)\.([A-Z0-9_]+)$")


def is_valid_id(rule_id: str) -> bool:
    """`EN.<ALAN>.<KURAL>` bicimini VE `<ALAN>`in kapali listede olmasini
    denetler. Bicim gecerli olsa bile bilinmeyen bir ALAN reddedilir."""
    match = _ID_RE.match(rule_id)
    if not match:
        return False
    area, _rule = match.groups()
    return area in AREAS


@dataclass(frozen=True)
class GrammarRule:
    """Katalogdaki TEK satir. Kodda/veride durur, depoda DEGIL (§7)."""

    #: `EN.<ALAN>.<KURAL>` — HIC DEGISMEZ, birlestirme bile bunu silmez.
    id: str
    #: Kuralin genel adi (bir kez yazilir, her cumlede yeniden odenmez).
    name_en: str
    #: 1-2 cumlelik genel aciklama.
    short_en: str
    #: Kuralin ogretildigi CEFR bandi.
    level: str
    #: Bu bandin USTUNDEKI bir cumlede artik "goze carpan" sayilmaz.
    assume_known_from: str
    #: `rank=1`de ASLA gorunemeyecek kurallar (kopula, tanimlik, cogul -s).
    trivial: bool = False
    #: Bos ya da baska bir id — BIRLESTIRME BURADAN yapilir, satir silinmez.
    merged_into: str | None = None

    def __post_init__(self) -> None:
        """Katalog satiri YAZILIRKEN id biciminin gecerli oldugunu garanti eder."""
        if not is_valid_id(self.id):
            raise ValueError(f"gecersiz kural id'si: {self.id!r}")
        if self.merged_into is not None and not is_valid_id(self.merged_into):
            raise ValueError(
                f"gecersiz merged_into id'si: {self.merged_into!r}")
