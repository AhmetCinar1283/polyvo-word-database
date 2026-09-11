"""
Zorluk bandi SOZLESMESI — prompt ile QA'nin TEK ortak kaynagi.

Olculmeyen istek tutulmaz: bandi modele yazan (`prompt.py`) ve cevapta olcen
(`qa/level.py`) ayni sabitten okur, yoksa "kisa cumle" iki dosyada iki farkli
sey olur.

Zorluk SIK SAYISINDAN GELMEZ — ucu de 4 siktir. Zorlugu iki sey belirler:
cumle uzunlugu ve CELDIRICI YAKINLIGI. Secenek sunmak soruyu kolaylastirir
(tanima, hatirlamadan kolaydir); zor soru ancak celdiriciler gercekten yakin
anlamliysa zordur.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    """Tek bir zorluk bandi: adi, cumle uzunlugu araligi, celdirici tarifi."""

    name: str
    min_words: int
    max_words: int
    distractor_hint: str
    purpose: str
    #: Celdiricinin CEFR tavani bu bandda REDDEDER mi, yoksa yalnizca UYARIR
    #: mi. "zor"da uyarir: o bandin tarifi YAKIN ANLAMLI celdiricidir ve bir
    #: A1 kelimesinin yakin anlamlilari tanim geregi daha seyrektir. Iki
    #: istegi ayni anda tutmak imkansizdir; tutulamayan sey reddetmez (§6.7).
    enforce_distractor_level: bool


#: Sira ANLAMLIDIR: uretilen sorularin `seq`i (1,2,3) bu siradir ve hangi
#: cevabin hangi zorluk oldugu SABITTIR — zorluk etiketi modelden gelmez,
#: istekte biz veririz.
#: `distractor_hint` PROMPT'A GIRER, bu yuzden Ingilizcedir; Turkce karsiligi
#: `purpose`un yanindaki aciklamadir (kolay: uzak celdirici / orta: ilgili ama
#: uymuyor / zor: yakin anlamli).
BANDS: tuple[Band, ...] = (
    Band("kolay", 5, 9,
         "FAR from the target — clearly from a different area of meaning",
         "kelimeyi taniyor mu", enforce_distractor_level=True),
    Band("orta", 9, 15,
         "a related area, but plainly wrong in this sentence",
         "anlami ayirt ediyor mu", enforce_distractor_level=True),
    Band("zor", 15, 25,
         "NEAR-SYNONYMS — close in meaning, wrong in this use",
         "nerede kullanildigini biliyor mu", enforce_distractor_level=False),
)

#: Anlam basina uretilecek soru sayisi (= band sayisi).
QUESTION_COUNT = len(BANDS)

#: Her soruda bulunmasi gereken sik sayisi: 1 dogru cevap + 3 celdirici.
OPTION_COUNT = 4


def band_for(seq: int) -> Band:
    """`seq` (1'den baslar) icin zorluk bandi."""
    return BANDS[seq - 1]


def names() -> tuple[str, ...]:
    """Zorluk adlari, uretim sirasinda."""
    return tuple(b.name for b in BANDS)
