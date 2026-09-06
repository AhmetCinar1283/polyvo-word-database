"""
Aday eleme — bir kelimenin evrene girip girmeyecegine karar verilen tek yer.

Kural: SESSIZ ELEME YOK. Her fonksiyon ya `None` (kabul) ya da bir SEBEP
dizesi doner; sebep `unresolved` tablosuna yazilir ve rapora girer
(MIGRATION-PLAN §6.1). Boylece "9.981 bekliyordum, 9.418 cikti" sorusunun
cevabi her zaman veritabaninin icindedir.

Bu eleme ogretim amaclidir, dil bilimsel degil: kaynaklar dil bilim/altyazi
kokenli oldugu icin icinde ogrenciye gosterilemeyecek satirlar var (olculdu:
kisaltma girdileri, tek harfli semboller, rakam iceren bantlar).
"""

from __future__ import annotations

import re

#: Ogretimde tek basina anlamli olan tek harfli kelimeler. Digerleri
#: (`b`, `x`, `k`...) kaynak artigidir.
_ONE_LETTER_OK = frozenset({"a", "i"})

#: Harf, bosluk, kesme ve tire disinda bir sey varsa bu bir kelime degildir.
#: Aksanli latin harfleri KABUL EDILIR: `cafe`/`entree` ingilizce ders
#: kitaplarinda gecen alinti kelimelerdir, kaynak artigi degil.
_ALLOWED = re.compile(r"^[a-zÀ-ɏ][a-zÀ-ɏ' \-.]*$")

#: `a.m.`, `p.m.`, `etc.` gibi noktali kisaltmalar ogretilebilir birimlerdir,
#: ama `u.s.a.`-tipi ozel ad kisaltmalari degil. Ayrimi nokta sayisi degil
#: beyaz liste yapar — tahmin etmiyoruz.
_DOTTED_OK = frozenset({"a.m.", "p.m.", "etc.", "e.g.", "i.e."})

#: Kaynaklarda olculen kelime-disi girdiler.
_STOP_TOKENS = frozenset({"", "-", "'"})

#: Ogretim birimi olarak fazla uzun. CEFR-J'de 5+ kelimelik "kalip" satirlari
#: var; bunlar kelime degil ifade kaliplaridir ve baska bir modulun isidir.
MAX_WORDS = 3


def reject_reason(headword: str) -> str | None:
    """Kabul edilirse `None`, edilmezse makine-okunur bir sebep doner."""
    if headword in _STOP_TOKENS:
        return "bos"
    if headword in _DOTTED_OK:
        return None
    if len(headword) == 1 and headword not in _ONE_LETTER_OK:
        return "tek_harf"
    if any(ch.isdigit() for ch in headword):
        return "rakam_iceriyor"
    if not _ALLOWED.match(headword):
        return "kelime_disi_karakter"
    if headword.endswith("."):
        return "kisaltma"
    if len(headword.split()) > MAX_WORDS:
        return "cok_uzun"
    return None


def is_acceptable(headword: str) -> bool:
    """`reject_reason` bos donuyor mu — kisa kontrol icin sozdizimsel seker."""
    return reject_reason(headword) is None
