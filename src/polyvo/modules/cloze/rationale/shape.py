"""
Ipucu/aciklama uzunluk bandi SOZLESMESI — prompt ile QA'nin TEK ortak kaynagi.

`difficulty.py` deseni: bant burada bir kez tanimlanir, hem prompt'u kuran
hem cevabi olcen ayni sabitten okur (V2-IS-5 §10). Bandi iki dosyaya yazmak
yasaktir.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LengthBand:
    """Kelime sayisi cinsinden kabul edilebilir uzunluk araligi."""

    min_words: int
    max_words: int


#: Ipucu KISA olmali — cevabi SOYLEMEDEN yol gostermenin dogasi budur (§8).
HINT_BAND = LengthBand(min_words=3, max_words=20)

#: Aciklama ipucundan UZUN olabilir — "neden bu, neden digerleri degil"
#: sorusunu yanitlamak ipucundan daha cok soz ister (§9).
REASON_BAND = LengthBand(min_words=4, max_words=40)
