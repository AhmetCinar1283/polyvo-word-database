"""
Uretilen L2 metni uzerinde calisan, LLM GEREKTIRMEYEN ortak metin yardimcilari
(hedef kelime metinde geciyor mu, cumle bolme, yuzey-bicim karsilastirma).
Kopyalamak yerine tek yerde — bir kelimenin "gectigi" karari her cagiran
dosyada ayni olmali.

DIKKAT: prompt METNINE girmez, sadece cikti denetler — burayi degistirmek
`llm_cache`i gecersizlestirmez.
"""

import re
import unicodedata

__all__ = [
    "ENGLISH_MARKERS",
    "english_marker_hits",
    "morphy_roots",
    "find_spans",
    "mentions_target",
    "split_sentences",
    "surface_pattern",
    "normalized_hash_text",
    "fold_for_match",
    "shared_prefix_len",
    "loose_same_word",
    "MIN_SHARED_PREFIX",
]

# Ingilizce oldugunu dogrulamak icin ucuz sinyal: bu fonksiyon kelimelerinin
# (zamir/yardimci fiil/edat/baglac/soru) hicbiri gecmiyorsa metin muhtemelen
# yanlis dilde. Liste genis tutuldu — dogal bir Ingilizce cumlenin HICBIRINI
# icermemesi pratikte imkansiza yakin, gercek yanlis-dil yine de yakalanir.
ENGLISH_MARKERS = re.compile(
    r"\b("
    r"the|a|an|and|or|but|nor|so|if|as|than|then|that|this|these|those|"
    r"was|were|is|are|am|be|been|being|do|does|did|done|"
    r"has|have|had|will|would|can|could|should|must|may|might|shall|"
    r"to|of|in|on|with|for|at|by|from|into|onto|about|after|before|"
    r"between|through|during|without|within|over|under|up|down|out|off|"
    r"i|you|he|she|it|we|they|me|him|her|us|them|"
    r"my|your|his|its|our|their|mine|yours|hers|ours|theirs|"
    r"not|no|yes|there|here|when|where|what|who|whom|which|why|how|"
    r"all|any|some|each|every|both|either|neither|more|most|other|another|"
    r"one|two|first|new|get|got|go|went|make|made|take|took|see|saw|"
    r"know|knew|like|want|need|come|came|look|also|just|only|very|"
    r"because|while|although|s|re|ve|ll|d|t|m"
    r")\b",
    re.IGNORECASE,
)


def english_marker_hits(text: str, ambiguous: frozenset[str] = frozenset()) -> int:
    """Metindeki AYIRT EDICI Ingilizce isaretcilerinin sayisi.

    `ambiguous` hedef dilde DE gecen isaretcilerdir (Ispanyolca "a"/"no",
    Almanca "in", Portekizce "a"/"no") ve SAYILMAZ. OLCULDU (2026-09-07):
    bu ayiklama yapilmadiginda dil kapisi DOGRU cevirileri reddediyordu —
    bu kelimelerin bir Ispanyolca/Almanca/Portekizce cumlede hic gecmemesi
    imkansiza yakindir, yani kapinin "Ingilizce kaniti" tarafi her zaman
    ateslenip karari tek basina L1 isaretcisine birakiyordu.
    """
    return sum(1 for m in ENGLISH_MARKERS.finditer(text or "")
               if m.group(0).lower() not in ambiguous)


_VOWELS = "aeiou"


def _inflected_forms(headword: str) -> list[str]:
    """Hedef kelimenin olasi yuzey formlari: kok + duzenli Ingilizce cekim
    ekleri (-s/-ed/-ing/-'s, e-dusmesi, CVC ikizlenmesi, y->ied/ies).
    Tam morfoloji degil, bilinen kaliplar icin yeterli bir yaklasim."""
    base = headword.lower()
    forms = {base, base + "s", base + "es", base + "d", base + "ed", base + "ing", base + "'s"}

    if len(base) >= 2 and base[-1] == "e" and base[-2] not in _VOWELS:
        forms.add(base[:-1] + "ing")

    if (
        len(base) >= 3
        and base[-1] not in _VOWELS
        and base[-1] not in "wxy"
        and base[-2] in _VOWELS
        and base[-3] not in _VOWELS
    ):
        doubled = base + base[-1]
        forms.add(doubled + "ed")
        forms.add(doubled + "ing")

    if len(base) >= 2 and base[-1] == "y" and base[-2] not in _VOWELS:
        forms.add(base[:-1] + "ied")
        forms.add(base[:-1] + "ies")

    # Uzun formlar once denenmeli, yoksa alternation kisa bir onekte durup
    # gerideki -e/-ing kalibini hic gormeden eslesir.
    return sorted(forms, key=len, reverse=True)


def surface_pattern(headword: str) -> re.Pattern:
    """Hedef kelimenin metinde gecip gecmedigini kontrol icin gevsek bir
    duzenli ifade: kok + yaygin cekim ekleri. Tam morfolojik analiz degil —
    F4/F5 pilotu icin yeterli bir yaklasim, bilinen bir sinirlama (bkz. rapor)."""
    alternatives = "|".join(re.escape(form) for form in _inflected_forms(headword))
    return re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)


def find_spans(text: str, headword: str) -> list[tuple[int, int, str]]:
    """(char_start, char_end, surface_form) listesi, verilen kok icin."""
    return [(m.start(), m.end(), m.group(0)) for m in surface_pattern(headword).finditer(text)]


_WORD_RE = re.compile(r"[A-Za-z']+")
# TURETME EKLERI BILEREK YOK: CEKIM (mean/meant) AYNI kelimedir ve eslesmeli,
# TURETME (health/healthy) BASKA kelimedir ve eslesMEMELI (farkli POS/lemma).
# `wn.morphy` yalnizca cekim cozer, bu yuzden dogru arac budur.


def morphy_roots(token: str) -> set[str]:
    """`token`un WordNet'e gore olasi kokleri (duzensiz cekimler icin —
    mean->meant, leave->left — regex bunlari kapsayamaz). WordNet yoksa bos kume.

    ILAN EDILMIS yuzeydedir cunku iki ayri soru ayni cevabi ister: "bu kelime
    hedef kelimenin bir bicimi mi" (burasi) ve "bu kelimenin CEFR'i ne"
    (`modules/cloze/cefr.py`). Ikinci cagiran olmasaydi ozel kalirdi; iki
    kopya cekim cozumu ayrisirdi."""
    try:
        from nltk.corpus import wordnet as wn
    except Exception:
        return set()
    roots = set()
    for pos in ("v", "n", "a", "r"):
        try:
            root = wn.morphy(token.lower(), pos)
        except Exception:
            return set()
        if root:
            roots.add(root)
    return roots


def find_spans_loose(text: str, headword: str) -> list[tuple[int, int, str]]:
    """`find_spans` + duzensiz cekimler (meant->mean, left->leave). Cloze icin
    gerekli: orada hedef kelimenin TAM KONUMU lazim, sadece varligi degil."""
    spans = find_spans(text, headword)
    if spans:
        return spans
    base = headword.lower()
    out = []
    for m in _WORD_RE.finditer(text):
        if base in morphy_roots(m.group(0)):
            out.append((m.start(), m.end(), m.group(0)))
    return out


def mentions_target(text: str, headword: str) -> bool:
    """Hedef kelime metinde geciyor mu — `find_spans`ten DAHA gevsek: duzenli
    cekim + WordNet kok esitligi (yalnizca cekim, turetme DEGIL). Bu bir RED
    sebebi degil UYARI — yanlis pozitifin maliyeti dusuk, yanlis reddin yuksek."""
    if find_spans(text, headword):
        return True
    base = headword.lower()
    for token in _WORD_RE.findall(text):
        tok = token.lower()
        if tok == base or base in morphy_roots(tok):
            return True
    return False


def split_sentences(text: str) -> list[str]:
    """Basit cumle bolucu — kisaltmalari tam ele almaz, pilot icin yeterli."""
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def normalized_hash_text(text: str) -> str:
    """Tekrar tespiti icin normalize metin (bosluk daraltilmis, kucuk harf) —
    hash'in kendisi degil, hash'e girecek girdi."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


# DIL-BAGIMSIZ yuzey karsilastirmasi — terim tutarlilik kapisi icin taban.
# Amac: sozlukteki bicim ("kulak") ile cekimli cumledeki bicimi ("kulağımla")
# birbirine YAKIN sayabilmek. Tam esitlik/onek yetmez (unsuz yumusamasi,
# unlu dusmesi, diyakritik farki onegi kirar) — cozum PAYLASILAN ONEK UZUNLUGU.
# Hata yonu bilincli: FAZLA eslesmek kabul edilir, YANLIS ALARM edilmez.
#
# SONEKLI dillerde (kok basta) gecerlidir; on-ekli dillerde (Almanca, Rusca)
# gecerli degildir — bu yuzden `lang/<l1>.TERM_MATCH_SUPPORTED` acikca
# isaretlemeyen dilde bu kapi hic calismaz.

MIN_SHARED_PREFIX = 3

# Turkce'nin noktasiz `ı`si NFKD ile `i`ye inmez (diyakritikli degil, kendi
# kod noktasi) — acikca eslenir. Buyuk `İ` icin NFKD zaten yeterli.
_FOLD_EXTRA = {"ı": "i"}


def fold_for_match(word: str) -> str:
    """Karsilastirma icin normalize kelime: kucuk harf, diyakritiksiz, yalniz
    alfanumerik. BILEREK bilgi kaybettirir (fazla eslesme yonunde) — kapinin
    kabul ettigi yon budur."""
    w = (word or "").strip().lower()
    for src, dst in _FOLD_EXTRA.items():
        w = w.replace(src, dst)
    w = unicodedata.normalize("NFKD", w)
    w = "".join(ch for ch in w if not unicodedata.combining(ch))
    return "".join(ch for ch in w if ch.isalnum())


def shared_prefix_len(a: str, b: str) -> int:
    """Iki dizenin ortak onek uzunlugu (karakter)."""
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n


def loose_same_word(a: str, b: str, min_shared: int = MIN_SHARED_PREFIX) -> bool:
    """Iki yuzey bicim AYNI sozcugun bicimleri OLABILIR mi (morfolojik
    cozumleyici degil). Kural: esit, ya da biri digerinin oneki (>=2 harf),
    ya da ortak onek >= `min_shared`."""
    fa, fb = fold_for_match(a), fold_for_match(b)
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    n = shared_prefix_len(fa, fb)
    if n >= 2 and n == min(len(fa), len(fb)):
        return True
    return n >= max(2, min_shared)
