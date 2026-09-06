"""
Normalize kurallari — kaynaklar arasi POS/CEFR uyusmazliginin TEK cozuldugu
yer (her kaynak kendi sozlugunu kullanir, kural burada bir kez cozulur).

BILINMEYEN POS SESSIZCE ATLANMAZ: `normalize_pos` `None` doner, cagiran
onu `unresolved` tablosuna yazar (MIGRATION-PLAN §6.1).
"""

from __future__ import annotations

import re
import unicodedata

# ── POS ───────────────────────────────────────────────────────────────────

#: Kanonik POS kumesi. Bu kume KIMLIGIN parcasidir (K1): degistirmek
#: `items` anahtarini degistirir, yani yayinlanmis kimligi bozar.
CANONICAL_POS: frozenset[str] = frozenset({
    "noun", "verb", "adj", "adv", "pron", "prep", "det",
    "conj", "num", "interj", "modal", "particle",
})

#: Kaynak etiketi -> kanonik POS. Kaynak adi ne olursa olsun ayni tablo
#: kullanilir; bir kaynagin "kendine ozel" esleme ihtiyaci varsa o bir
#: kaynak tuhafligidir ve ingestor'unda cozulur, burada degil.
POS_MAP: dict[str, str] = {
    # CEFR-J
    "noun": "noun",
    "adjective": "adj",
    "verb": "verb",
    "adverb": "adv",
    "pronoun": "pron",
    "preposition": "prep",
    "determiner": "det",
    "conjunction": "conj",
    "number": "num",
    "interjection": "interj",
    "modal auxiliary": "modal",
    # `be`/`do`/`have` ogretim acisindan fiildir; ayri POS yapmak `be` icin
    # ayri bir kart ailesi dogurur ve hicbir sey kazandirmaz.
    "be-verb": "verb",
    "do-verb": "verb",
    "have-verb": "verb",
    # Tek satir: "to". Fiil olmadigi icin `particle`.
    "infinitive-to": "particle",
    # Kisa biçimler (legacy_dist ve OEWN bu bicimi kullanir)
    "adj": "adj", "adv": "adv", "pron": "pron", "prep": "prep",
    "det": "det", "conj": "conj", "num": "num", "interj": "interj",
}

#: ACIKCA beyan edilmis yazim hatasi duzeltmeleri. Bunlari `POS_MAP`'e
#: karistirmiyoruz: bir yazim hatasini duzeltmek ile bir etiketi eslemek
#: farkli seylerdir ve ilkinin kaynakta duzelmesi beklenir.
POS_TYPO_FIXES: dict[str, str] = {
    "vern": "verb",        # Octanove 1.0, 1 satir
}


def normalize_pos(raw: str | None) -> str | None:
    """Kaynak POS etiketini kanonik bicime cevirir.

    `None` doner: etiket bos, taninmiyor veya duzeltilemiyor. Cagiranin bunu
    RAPORLAMASI gerekir — sessizce atmasi degil.
    """
    if not raw:
        return None
    key = " ".join(raw.strip().lower().split())
    if not key:
        return None
    key = POS_TYPO_FIXES.get(key, key)
    mapped = POS_MAP.get(key)
    if mapped is None and key in CANONICAL_POS:
        return key
    return mapped


# ── Headword ──────────────────────────────────────────────────────────────

#: Kaynaklarda olculdu: `'turn to '` (sonda bosluk), `'all right'` iki kez.
#: Temizlik bu yuzden bir "olsa iyi olur" degil, bir gereklilik.
_WS = re.compile(r"\s+")


def normalize_headword(raw: str) -> str | None:
    """Bosluk/tire/kucuk harf normalizasyonu. Gecersizse `None`."""
    if not raw:
        return None
    # NFKC: kaynaklarda tipografik kesme (U+2019) ve tam-genislik karakter var.
    text = unicodedata.normalize("NFKC", raw).strip()
    text = text.replace("’", "'").replace("‘", "'")
    text = _WS.sub(" ", text).lower()
    return text or None


#: Iki kaynak (CEFR-J 167 satir, Octanove 50 satir) yazim varyantlarini TEK
#: hucrede egik cizgiyle veriyor: `analyze/analyse`. Bu bir kaynak tuhafligi
#: degil, iki kaynagin PAYLASTIGI bir bicimdir — kural burada durur.
def split_variants(raw: str) -> list[str]:
    """`analyze/analyse` -> `["analyze", "analyse"]`. Ilki birincil bicimdir."""
    return [part for part in (p.strip() for p in (raw or "").split("/")) if part]


def is_multiword(headword: str) -> bool:
    """Baslik bosluk iceriyor mu (orn. "bank account")."""
    return " " in headword


# ── CEFR ──────────────────────────────────────────────────────────────────

CEFR_ORDER: dict[str, int] = {
    "A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6,
}


def normalize_cefr(raw: str | None) -> str | None:
    """Ham CEFR etiketini buyuk harfe cevirir; taninmiyorsa `None`."""
    if not raw:
        return None
    key = raw.strip().upper()
    return key if key in CEFR_ORDER else None


def merge_cefr(*levels: str | None) -> str | None:
    """K6: dusuk seviye kazanir — kelimeyi kolay saymak zor saymaktan az
    zararli (erken karsilasip tekrar eder, tersi hic karsisina cikmaz)."""
    known = [lv for lv in (normalize_cefr(x) for x in levels) if lv]
    if not known:
        return None
    return min(known, key=lambda lv: CEFR_ORDER[lv])


def merge_tier(*tiers: int | None) -> int | None:
    """Bir kelime birden cok listede geciyorsa EN DUSUK tier kazanir —
    tier "bu kelime ne kadar cekirdek" demektir, "hangi dosyadan geldi" degil."""
    known = [t for t in tiers if t is not None]
    return min(known) if known else None
