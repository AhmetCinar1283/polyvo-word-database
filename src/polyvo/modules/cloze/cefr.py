"""
KELIME -> CEFR sozlugu ve seviye karsilastirmasi.

Kaynak `builds/<tag>/01_lexicon/lexicon.sqlite` icindeki `candidates`
tablosudur (11.009 kelime + `cefr`): "bizim evrenimizdeki kelime" tam olarak
budur. Odenmis depo (`lexicon.sqlite`) DEGIL — orada yalnizca kosulan 1000
kelime var, celdirici ise evrenin herhangi bir kelimesi olabilir.

Sozlukte seviye KELIME BASINA DEGIL (kelime, POS) BASINA bilinir: `take`
fiil olarak A1, isim olarak B1'dir. POS bilindiginde o satir kullanilir;
bilinmediginde (cumledeki serbest kelimeler) kelimenin EN DUSUK seviyesi
kullanilir — ogrenci kelimeyi ilk orada gorur.

BILINMEYEN SEVIYE BIR RED GEREKCESI DEGILDIR. 1000 kelimenin 160'inda `cefr`
yok; "bilmiyorum" bir satiri cope attirmaz (V2-IS-4 §10). Bu dosya bunu
`None` dondurerek soyler, karari cagirana birakir.
"""

from __future__ import annotations

import os
import sqlite3

from polyvo.core.text import qa as text_qa

#: Kucukten buyuge CEFR siralamasi. Listede olmayan bir etiket "bilinmiyor".
LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

_ORDER = {name: i for i, name in enumerate(LEVELS)}

#: Tavan kapilarinin verdigi BAND PAYI: hedefin seviyesini tam bir band asan
#: kelime reddetmez. Sifir tolerans A1 anlamlar icin tutulamaz bir sozdur —
#: bir A1 kelimesinin yakin anlamlilari tanim geregi daha seyrektir (A2+),
#: yani "yakin anlamli celdirici" istegiyle "celdirici A1 olsun" istegi ayni
#: anda tutulamaz. Iki band asma hala reddeder.
LEVEL_TOLERANCE = 1

#: `db_path -> Levels` — ayni kosuda tekrar tekrar okunmasin.
_cache: dict[str, "Levels"] = {}


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


class Levels:
    """Evrenin seviye sozlugu: `(kelime, pos)` ve kelime bazli iki okuma.

    `dict` degil kucuk bir sinif, cunku iki farkli soru sorulur ve ikisinin
    cevabi ayni degildir: celdiricinin POS'u BILINIR (hedefle ayni olmak
    zorunda), cumledeki serbest kelimenin POS'u bilinmez."""

    def __init__(self, by_pos: dict[tuple[str, str], str],
                 lowest: dict[str, str]):
        """Iki haritayi sarar; ikisi de `load` icinde tek gecisle kurulur."""
        self._by_pos = by_pos
        self._lowest = lowest

    def _surface(self, word: str, pos: str | None) -> str | None:
        """TEK bir yuzey bicimin seviyesi — cekim cozumu YOK."""
        if pos is not None:
            level = self._by_pos.get((word, pos.strip().lower()))
            if level is not None:
                return level
        return self._lowest.get(word)

    def get(self, word: str, pos: str | None = None) -> str | None:
        """Kelimenin seviyesi; bilinmiyorsa `None`.

        POS verilirse once o satir aranir, yoksa kelimenin en dusuk seviyesine
        dusulur — POS'u sozlukte olmayan bir kelimeyi "bilinmiyor" saymak
        olculebilir bir bilgiyi cope atmak olurdu.

        CEKIMLI BICIM KOKUNE INDIRILIR ve yuzey ile kokun DUSUGU kazanir.
        Sozlukte cekimli bicimler AYRI VE DAHA YUKSEK satirlar olarak
        bulunabiliyor: `removed` C1 iken `remove` B1, `took`/`bought` hic yok
        iken `take`/`buy` A1. Cekimi cozmeyen bir arama, dogru bir celdiriciyi
        yalnizca gecmis zamanda yazildigi icin "seviyenin ustunde" sayardi —
        2026-09-07 kosusunda `add` fiili tam bunun yuzunden reddedildi
        (`removed` C1 okundu).

        Dusugun kazanmasi, sinifin geri kalaniyla AYNI yon: ogrenci kelimeyi
        ilk gordugu yerde ogrenir, ve olculemeyen/suphe edilen sey reddetmez.
        Yalnizca CEKIM cozulur, TURETME degil (`wn.morphy`) — `health` ile
        `healthy` ayri kelimelerdir ve seviyeleri de ayridir."""
        key = word.strip().lower()
        candidates = [self._surface(key, pos)]
        for root in text_qa.morphy_roots(key):
            if root != key:
                candidates.append(self._surface(root, pos))

        best: str | None = None
        best_order: int | None = None
        for level in candidates:
            order = rank(level)
            if order is not None and (best_order is None or order < best_order):
                best, best_order = level, order
        return best

    def __len__(self) -> int:
        """Sozlukteki farkli kelime sayisi (testler ve tanilar icin)."""
        return len(self._lowest)


def load(db_path: str) -> Levels:
    """Build sozlugunden seviye haritasi.

    Dosya yoksa BOS sozluk doner: seviye kapisi bir KOLAYLIKTIR, yoklugu
    kosuyu durdurmaz — yalnizca olcum yapilamaz."""
    if db_path in _cache:
        return _cache[db_path]

    by_pos: dict[tuple[str, str], str] = {}
    lowest: dict[str, str] = {}
    if os.path.exists(db_path):
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            for headword, pos, level in conn.execute(
                    "SELECT headword, pos, cefr FROM candidates"
                    " WHERE cefr IS NOT NULL AND cefr != ''"):
                key = str(headword).strip().lower()
                value = str(level).strip().upper()
                order = rank(value)
                if order is None:
                    continue          # tanimadigimiz etiket: olcum yok
                by_pos[(key, str(pos).strip().lower())] = value
                # Ayni kelime birden cok POS'la gelebilir: EN DUSUK seviye
                # kazanir. Karsilastirma `rank(...) is None` ile yapilir —
                # `or 99` yazilirsa A1'in sirasi 0 oldugu icin YANLIS tarafa
                # duser ve A1 her karsilastirmayi KAYBEDER.
                current = rank(lowest.get(key))
                if current is None or order < current:
                    lowest[key] = value
        except sqlite3.Error:
            by_pos, lowest = {}, {}   # bozuk/eski build: olcum yok, red yok
        finally:
            conn.close()

    _cache[db_path] = Levels(by_pos, lowest)
    return _cache[db_path]


def reset_cache() -> None:
    """Onbellegi bosaltir — testler kendi `tmp_path`ini kullanabilsin diye."""
    _cache.clear()
