"""
CEFR seviye siralamasi + karsilastirmasi — `cloze/cefr.py`nin KUCUK bir
KOPYASI (ayni mantik, tek fonksiyon).

NEDEN KOPYA: `grammar` hicbir kardes `modules/*` paketini import EDEMEZ
(demir kural, Is 6 §A2); seviye siralamasi gibi kucuk, saf bir yardimci icin
ikinci bir app'e bagimlilik acmaya degmez. Temiz cozum bu mantigin
`core/lang/`e tasinmasidir — o tasima AYRI bir isin konusudur (ayni tuzak
`cloze/translate/language.py`nin docstring'inde de kayitlidir).
"""

from __future__ import annotations

#: Kucukten buyuge CEFR siralamasi. Listede olmayan bir etiket "bilinmiyor".
LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

_ORDER = {name: i for i, name in enumerate(LEVELS)}


def rank(level: str | None) -> int | None:
    """CEFR etiketinin sira numarasi; bilinmeyen/bos etikette `None`."""
    if not level:
        return None
    return _ORDER.get(level.strip().upper())


def exceeds(candidate: str | None, ceiling: str | None,
            tolerance: int = 0) -> bool:
    """`candidate` seviyesi `ceiling`i `tolerance` banddan FAZLA asiyor mu?

    Iki taraftan biri bilinmiyorsa `False` — olculemeyen sey reddedilmez."""
    a, b = rank(candidate), rank(ceiling)
    if a is None or b is None:
        return False
    return a > b + tolerance
