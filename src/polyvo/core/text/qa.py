"""
Uretilen L2 metni uzerinde calisan, LLM GEREKTIRMEYEN ortak metin yardimcilari.

`paragraph_gen.py` (F4/F5), `cloze_gen.py` (F5) ve `translation_sync.py` (F6)
ayni yuzey-bicim eslestirmesini ve ayni cumle bolucusunu kullanir. Kopyalamak
yerine tek yerde tanimli: bir kelimenin metinde "gectigi" kararinin uc dosyada
farkli davranmasi, span'lerin (dolayisiyla cloze bosluklarinin ve dokunma
hedeflerinin) sessizce kaymasi demekti.

DIKKAT: buradaki hicbir fonksiyon prompt METNINE girmez — sadece cikti
denetimi yapar. Bu yuzden burayi degistirmek `llm_cache`'i GECERSIZLESTIRMEZ
(prompt degisiklikleri gecersizlestirir, bkz. MASTER_PLAN § 5/ZORUNLU 3).
"""

import re
import unicodedata

__all__ = [
    "ENGLISH_MARKERS",
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

# Ingilizce oldugunu dogrulamak icin ucuz bir sinyal: bu kok kelimelerden
# hicbiri gecmiyorsa metin muhtemelen yanlis dilde ya da bozuk.
#
# 2026-08-17: genisletildi. Eski liste (~16 kelime) gercek Ingilizce cumleleri
# de kacirabiliyordu — orn. "She quickly jumped over that fence!" listedeki
# hicbir kelimeyi icermiyor ve yanlis dil sanilip reddediliyordu (retry artik
# YOK, bkz. MAX_ATTEMPTS notu — yanlis red artik bir sonraki denemede kendini
# duzeltmiyor, dogrudan kalici reddedilmis satir oluyor). Liste artik
# Ingilizce'nin en yaygin fonksiyon kelimelerinin (zamir, yardimci fiil, edat,
# baglac, soru kelimesi) buyuk cogunlugunu kapsiyor — dogal bir Ingilizce
# cumlenin bunlarin HICBIRINI icermemesi pratikte imkansiza yakin, ama
# gercekten yanlis dildeki (orn. tamamen Turkce/baska dil) bir cikti yine de
# yakalanir.
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


_VOWELS = "aeiou"


def _inflected_forms(headword: str) -> list[str]:
    """Hedef kelimenin olasi yuzey formlari: kok + yaygin cekim ekleri, ayrica
    Ingilizce'nin duzenli yazim degisikliklerini de kapsar (tam morfoloji
    degil — bariz, sik gorulen kaliplar icin yeterli bir yaklasim):

    - dogrudan ek: -s/-es, -d/-ed, -ing, -'s          (jump -> jumps/jumped)
    - sondaki 'e' -ing'den once dusuyor                (hope -> hoping)
    - CVC tek heceli fiillerde unsuz ikizlenmesi        (jam -> jammed/jamming)
    - unsuz+y -> -ied/-ies                              (try -> tried/tries)

    Onceki (`root + (e?s|e?d|ing|'s)?`) hali bu son iki kalibi hic
    yakalamiyordu: "jammed" icin "jam" + "ed" arasinda ikizlenmis "m" aradaydi,
    regex onu tek bir gecikmeli-eslesme olarak goremiyordu. Sonuc, LLM'in
    dogru urettigi bir cumlenin "hedef kelime cumlede yok" diye reddedilmesiydi
    (ekstra deneme = bosuna API cagrisi)."""
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
# TURETME EKLERI BILEREK YOK. (Ahmet, 2026-08-17: "healthy aslinda yanlis bir
# kelime burada da uyari almaliyim.") Ayrim dilbilimsel ve pedagojik olarak ayni
# yerden gecer:
#   CEKIM (inflection) = AYNI kelime, farkli gramer bicimi — meant/mean,
#     left/leave, children/child, jumps/jumped. Ogrenci hedef kelimeyle
#     KARSILASMIS sayilir, dolayisiyla eslesmeli.
#   TURETME (derivation) = BASKA bir kelime — healthy/health, musical/music,
#     independently/independent. Farkli lemma, cogu zaman farkli POS. Modul
#     zaten prompt'ta "bu kelimeyi ISIM olarak kullan" diyor (`_POS_PHRASE`),
#     yani `health` istenirken `healthy` gelmesi talimatin ihlali — tam olarak
#     Ahmet'in gormek istedigi durum.
# `wn.morphy` yalnizca cekim cozumler, bu yuzden dogru araç odur; ek bir
# turetme katmani eklemek uyariyi susturur, iyilestirmez.


def _morphy_roots(token: str) -> set[str]:
    """`token`un WordNet'e gore olasi kokleri. WordNet yoksa bos kume.

    Regex tabanli `_inflected_forms` DUZENLI cekimleri kapsar ama duzensizleri
    kapsayamaz (mean->meant, leave->left, man->men) — bunlar sonlu ama genis bir
    liste ve elle yazilmasi anlamsiz. WordNet'in `morphy`si bu tabloyu zaten
    tasiyor.
    """
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
    """`find_spans` + duzensiz cekimler (meant->mean, left->leave, children->child).

    Cloze icin gerekli: orada hedef kelimenin metinde GECMESI yetmez, tam
    KONUMU da lazim (bosluk oradan acilir), yani `mentions_target`in bool'u ise
    yaramaz. Regex bulursa o kullanilir; bulamazsa metnin her sozcugu WordNet
    `morphy` ile koke indirilip headword'e esit olanlarin span'i dondurulur.
    """
    spans = find_spans(text, headword)
    if spans:
        return spans
    base = headword.lower()
    out = []
    for m in _WORD_RE.finditer(text):
        if base in _morphy_roots(m.group(0)):
            out.append((m.start(), m.end(), m.group(0)))
    return out


def mentions_target(text: str, headword: str) -> bool:
    """Hedef kelime metinde geciyor mu — `find_spans`ten DAHA gevsek.

    Iki katman, ikisi de YALNIZCA cekim (bkz. yukaridaki turetme notu):
      1. `surface_pattern` (duzenli cekimler)  — jump/jumps/jumped/jumping
      2. WordNet `morphy` ile kok esitligi     — meant->mean, left->leave, children->child

    Turetilmis bicimler (healthy/health, musical/music) bilerek eslesMEZ:
    onlar baska kelimelerdir ve ogrenci hedef kelimeyle karsilasmis olmaz.

    NEDEN GEVSEK OLAN KISIM GEVSEK: bu kontrol bir RED sebebi degil, yalnizca
    bir UYARI (bkz. `paragraph_gen.run_qa`) — yanlis pozitifin maliyeti bir
    insan incelemesi, yanlis reddin maliyeti bosa giden API cagrilariydi.
    """
    if find_spans(text, headword):
        return True
    base = headword.lower()
    for token in _WORD_RE.findall(text):
        tok = token.lower()
        if tok == base or base in _morphy_roots(tok):
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
    """Tekrar tespiti icin normalize edilmis metin (bosluk daraltilmis, kucuk
    harf). Hash'in KENDISI degil, hash'e girecek metin — cagiran taraf istedigi
    hash fonksiyonunu uygular."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


# ===========================================================================
# DIL-BAGIMSIZ yuzey karsilastirmasi — F6 terim tutarliligi kapisi (2026-08-22)
# ===========================================================================
#
# NEDEN BURADA: bu blok L1 (ana dil) metnine bakar, oysa dosyanin geri kalani
# L2 (Ingilizce) uretimini denetler. Yine de buraya ait: icindeki hicbir kural
# BIR DILE OZGU DEGIL. Dile ozgu her sey `lang_rules/<l1>.py`de yasar
# (CLAUDE.md doktrini) — burasi o modulun UZERINE oturdugu taban.
#
# COZULEN HATA (olculdu 2026-08-22): terim kapisi sozlukteki bicimi
# ("çalışma", "kulak", "kâbus") cekimli cumlede ("çalışıyoruz", "kulağımla",
# "kabusla") ARIYOR ve bulamayinca satiri `quality='low'` isaretliyordu.
# 100 ornekli elle siniflandirmada bu tur MORFOLOJI kaynakli yanlis alarm
# %18 idi. Eski kod bunu "iki yonlu onek iliskisi" ile yakalamaya calisiyordu,
# ama onek iliskisi UC yerde kiriliyor:
#   1) unsuz yumusamasi   kulak  -> kulağımla   (k/ğ)
#   2) unlu dusmesi       keşif  -> keşfim
#   3) diyakritik/ASCII   kâbus  -> kabusla,  halı -> "hali" (bozuk gloss)
# Ucu de "ortak ONEK'in bir yerinde bir harf degisiyor" seklinde tezahur
# ediyor — yani cozum tam esitlik ya da onek DEGIL, PAYLASILAN ONEK UZUNLUGU.
#
# HATA YONU (degismedi, bilincli): kapi "bulunamadi" derse satir SUPHELI
# isaretlenir. Yani FAZLA eslesmek (gercek bir uyusmazligi kacirmak) kabul
# edilebilir; YANLIS ALARM kabul edilemez. Esikler bu yone gore secildi.
#
# GARANTI SINIRI — YENI L1 EKLERKEN OKU: buradaki mantik SONEKLI dillerde
# (kok basta kalir) gecerlidir. Almanca'nin `ge-` on ekli sifat-fiili
# (gehen -> gegangen, ortak onek "ge" = 2) ya da Rusca'nin on ekli fiilleri
# bu varsayimi bozar ve kapi HER cumleyi isaretlemeye baslar. Bu yuzden kapi
# `lang_rules/<l1>.TERM_MATCH_SUPPORTED` bayragini acikca isaretlemeyen bir
# dilde HIC CALISMAZ (bkz. translation_sync.gloss_appears_in). Guvenilmez bir
# uyari, uyari yoklugundan kotudur: kimse bakmaz, ama herkesin sayilarini
# bozar.

MIN_SHARED_PREFIX = 3

# Turkce'nin noktasiz `ı`si Unicode'da diyakritikli bir harf DEGILDIR (kendi
# kod noktasi), yani NFKD onu `i`ye indirgemez — acikca eslenmesi gerekir.
# Buyuk `İ`nin kucugu `i` + birlesik nokta oldugu icin NFKD zaten hallediyor.
_FOLD_EXTRA = {"ı": "i"}


def fold_for_match(word: str) -> str:
    """Karsilastirma icin normalize edilmis kelime: kucuk harf, diyakritiksiz,
    yalniz alfanumerik.

    `ş->s, ğ->g, ç->c, ö->o, ü->u, â->a, é->e` NFKD ile duser; `ı->i` elle
    eslenir. Ustunde durulacak nokta: bu katman BILEREK bilgi kaybettirir
    (Almanca `schön`/`schon` ayni yazilir hale gelir) — cunku kaybin yonu
    "fazla eslesme"dir ve kapinin kabul ettigi yon budur."""
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
    """Iki yuzey bicim AYNI sozcugun bicimleri olabilir mi?

    "Olabilir mi" — "midir" degil. Bu fonksiyon bir morfolojik cozumleyici
    DEGILDIR ve olmaya calismaz; tek isi bir uyari kapisinin yanlis alarm
    uretmesini engellemek.

    Kural (normalize edilmis bicimler uzerinde):
      1. esit                              -> True
      2. biri digerinin oneki (>= 2 harf)  -> True   ("ev" / "evde")
      3. ortak onek >= `min_shared`        -> True   ("kesif" / "kesfim")
    """
    fa, fb = fold_for_match(a), fold_for_match(b)
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    n = shared_prefix_len(fa, fb)
    if n >= 2 and n == min(len(fa), len(fb)):
        return True
    return n >= max(2, min_shared)
