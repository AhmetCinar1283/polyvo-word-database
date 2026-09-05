"""
Turkce (L1) bicim kurallari.

`tr_gloss.py`'nin govdesinden buraya tasindi (2026-08-14). Icerik aynen
korundu — sadece izole edildi, boylece diger diller bu kurallardan
etkilenmez ve yeni bir dil eklerken burasi ornek alinir.

BULGU (2026-08-14 dogruluk denetimi): 40 yuksek-guvenli ornegin elle
incelenmesinde ~%12-15'inin sessizce yanlis oldugu tespit edildi
(bathroom -> "tuvalet", forget -> "unut", plane -> "ucus" [dogrusu "ucak"],
piano -> "zayif"). Bunlarin yaklasik yarisi FIIL MASTAR HATASIYDI: model
"unutmak" yerine "unut" (emir kipi) donuyordu. `check_form`'un
`verb_missing_infinitive` kontrolu bu yarisini yakalar. Kalan yari saf
anlam hatasidir ve sezgisel bir kural ile yakalanamaz — onlar icin insan
denetimi (`review.py`) tek guvenilir yoldur.
"""

LANGUAGE_NAME = "Turkish"

# Cekim ekleri: bir sozluk girdisinde ASLA bulunmamasi gereken sonlar.
# (Fiil mastari `-mek/-mak` ile biter; asagidakiler cekimli hallerdir.)
_CONJUGATED_SUFFIXES = (
    "yor", "muş", "miş", "acak", "ecek", "malı", "meli",
    "dı", "di", "du", "dü", "tı", "ti", "tu", "tü",
)

_INFINITIVE_SUFFIXES = ("mek", "mak")

PROMPT_RULES = (
    "- Turkish verbs MUST be given in the infinitive, ending in \"-mek\" or \"-mak\" "
    "(e.g. \"gitmek\", \"unutmak\" — NOT \"gidiyor\", \"unut\", \"gitti\").\n"
    "- Nouns/adjectives/adverbs MUST be in the bare dictionary form: no plural "
    "\"-ler/-lar\", no possessive \"-i/-si\", no case endings \"-de/-den/-e\".\n"
    "- A multi-word Turkish phrase is fine when that is the natural equivalent "
    "(e.g. dinner -> \"akşam yemeği\")."
)

REVIEW_RULES = (
    "- pos='verb' ise karşılık MUTLAKA Türkçe mastar halinde olmalı (-mek/-mak):\n"
    "  \"koşmak\" DOĞRU, \"koşuyor\"/\"koşar\"/\"koş\" YANLIŞ.\n"
    "- pos noun/adj/adv ise çekimsiz temel biçim olmalı (çoğul/iyelik/hâl eki yok)."
)


def check_form(part_of_speech: str, text: str) -> str | None:
    """Turkce sozluk bicimi kapisi. Sorun varsa kisa kod, yoksa None.

    Cok kelimeli ifadelerde SON kelimeye bakilir ("akşam yemeği" -> "yemeği"),
    cunku Turkce'de bas (head) sondadir.
    """
    if not text:
        return None

    tail = text.strip().lower().split()[-1] if text.strip() else ""
    if not tail:
        return None

    is_infinitive = tail.endswith(_INFINITIVE_SUFFIXES)

    if part_of_speech == "verb" and not is_infinitive:
        return "verb_missing_infinitive"

    # Mastar zaten dogru bicim — `-mek`in icindeki "-me" cekim gibi gorunmesin.
    if is_infinitive:
        return None

    if tail.endswith(_CONJUGATED_SUFFIXES):
        return "looks_conjugated"

    return None


# ===========================================================================
# F6 (ceviri katmani) icin eklendi — 2026-08-15
# ===========================================================================

# Metnin gercekten Turkce oldugunu gosteren ucuz sinyaller. `text_qa.
# ENGLISH_MARKERS`'in aynadaki karsiligi: modelin ceviri yapmayip Ingilizce
# metni oldugu gibi geri vermesi ya da yanlis dile kaymasi bu kapiyla
# yakalanir. Iki yol da yeterlidir — Turkce'ye ozgu harfler ya da yaygin
# islev kelimeleri (kisa bir cumlede ozel harf hic gecmeyebilir:
# "Bu bir test." gibi).
import re as _re  # noqa: E402  (modul sonunda, ustteki saf-veri blogunu bozmamak icin)

# IKI TUZAK VAR, IKISI DE OLCULEREK BULUNDU (2026-08-15):
#
# 1) `re.IGNORECASE` BU DESENDE KULLANILAMAZ. Python'da 'ı'.upper() == 'I'
#    ve 'İ'.lower() == 'i' oldugu icin, IGNORECASE altinda `ı` ASCII `i` ile
#    ESLESIR — yani icinde 'i' gecen HER Ingilizce cumle "Turkce" gorunurdu
#    ("The dog ran fast in the garden" yanlislikla gecti). Bu yuzden ozel
#    harf sinifi BUYUK/KUCUK duyarlidir (iki hali de acikca listelenir),
#    kelime listesi ise `(?i:...)` ile yerel olarak duyarsizlastirilir.
#
# 2) Kelime listesinde INGILIZCE ile CAKISAN kelime/harf olamaz:
#    - "her" CIKARILDI — Ingilizce'de son derece yaygin ("her friend").
#    - Buyuk `I` CIKARILDI — Turkce'nin noktasiz buyuk I'si ASCII 'I' ile
#      AYNI kod noktasidir, yani Ingilizce "I think..." her seferinde
#      Turkce sayilirdi. Kucuk `ı` ve buyuk `İ` ayirt edici oldugu icin kaldi.
#    Ayrica diyakritiksiz yazilmis Turkce icin birkac ASCII yedek kelime
#    eklendi (hicbiri Ingilizce kelime degil).
LANG_MARKERS = _re.compile(
    r"[çğıöşüÇĞİÖŞÜ]"
    r"|(?i:\b(bir|ve|bu|şu|için|ile|olarak|daha|çok|ama|gibi|kadar|"
    r"sonra|önce|olan|değil|yok|mi|mı|degil|icin|cok)\b)"
)

# ---------------------------------------------------------------------------
# TERIM TUTARLILIGI KAPISI — dil yetenegi bildirimi (2026-08-22)
# ---------------------------------------------------------------------------
# F6'nin terim kapisi (`translation_sync.gloss_appears_in`) SADECE bu bayragi
# acikca `True` yapan dillerde calisir. Sessiz varsayilan `False`dir.
#
# NEDEN: kapinin altindaki karsilastirma (bkz. `text_qa.loose_same_word`)
# "kok BASTA kalir, ekler SONA gelir" varsayimina dayanir. Turkce icin bu
# dogru. Almanca'nin `ge-` on ekli sifat-fiili (gehen -> gegangen) ya da
# Rusca'nin on ekli fiilleri icin DEGIL — orada kapi her cumleyi
# "terim gecmiyor" diye isaretler ve `quality='low'` sayisi anlamsizlasir.
# Yeni bir L1 eklerken bu bayragi acmadan once o dilde OLCUM yapilmalidir:
# elle siniflandirilmis >=100 ornek uzerinde yanlis alarm orani.
TERM_MATCH_SUPPORTED = True

# Kok eslestirme icin soyulacak ekler — en uzun eslesen BIR kez soyulur.
# Tam morfolojik cozumleme DEGILDIR ve olmasi da gerekmiyor: buradaki tek is,
# "araba" glossu ile cumledeki "arabayla"nin ayni sozcuk oldugunu gorup
# TERIM TUTARLILIGI kapisini yanlis yere tetiklememek.
#
# HATA YONU BILINCLI SECILDI: kapi "bulunamadi" dediginde satiri SUPHELI
# isaretliyor. Yani fazla soymak (yanlis alarm) kabul EDILEMEZ, az soymak
# (kacirmak) kabul edilebilir. Bu yuzden:
#   - TEK HARFLI ekler (-ı/-i/-a/-e ...) listede YOK: "araba" -> "arab",
#     "evde" -> "evd" gibi kok bozulmalari uretiyorlardi (olculdu, 2026-08-15).
#   - Karsilastirma tam esitlik degil ONEK iliskisidir (bkz. asagidaki
#     docstring), boylece soyulamayan ekler yine de eslesir.
_MATCH_SUFFIXES = (
    "larından", "lerinden", "larıyla", "leriyle", "larında", "lerinde",
    "sının", "sinin", "sunun", "sünün",
    "ların", "lerin", "larda", "lerde", "lardan", "lerden",
    "ları", "leri", "lara", "lere", "lar", "ler",
    "ında", "inde", "unda", "ünde",
    "nın", "nin", "nun", "nün",
    "dan", "den", "tan", "ten",
    "yla", "yle", "ile",
    "da", "de", "ta", "te",
    "sı", "si", "su", "sü",
    "ya", "ye",
    # Fiil cekimleri (2026-08-22). Sozluk glossu MASTAR ("çalışmak"),
    # cumledeki bicim CEKIMLI ("çalışıyoruz") oldugu icin kapinin en sik
    # yanlis alarmi buradan geliyordu. Ekler UZUNDAN KISAYA denenir
    # (asagidaki `sorted(..., key=len, reverse=True)`), yani "ıyorum"
    # "yor"dan once soyulur.
    "ıyorum", "iyorum", "uyorum", "üyorum",
    "ıyoruz", "iyoruz", "uyoruz", "üyoruz",
    "ıyorsun", "iyorsun", "uyorsun", "üyorsun",
    "ıyor", "iyor", "uyor", "üyor", "yor",
    "acağını", "eceğini", "acağım", "eceğim", "acak", "ecek",
    "dığını", "diğini", "duğunu", "düğünü",
    "mıştı", "mişti", "muştu", "müştü",
    "mış", "miş", "muş", "müş",
    "dım", "dim", "dum", "düm", "tım", "tim", "tum", "tüm",
    "dık", "dik", "duk", "dük",
    "dı", "di", "du", "dü", "tı", "ti", "tu", "tü",
    "malı", "meli",
    "arak", "erek", "ince", "ınca", "unca", "ünce",
)

_MIN_STEM_LEN = 3


def stem_for_match(word: str) -> str:
    """Gevsek Turkce kok — SADECE metin ici arama karsilastirmasi icin.

    `check_form` sozluk BICIMINI denetler; bu fonksiyon ise iki yuzey bicimin
    ayni sozcuge ait olup olmadigini kabaca sorar. Fiil mastari (-mek/-mak)
    atilir, sonra listedeki en uzun ek BIR kez soyulur. Kok `_MIN_STEM_LEN`'in
    altina duserse soyma geri alinir.

    Cagiran taraf sonucu TAM ESITLIKLE degil, IKI YONLU ONEK iliskisiyle
    karsilastirmalidir: `a.startswith(b) or b.startswith(a)`. Ornekler
    (olculdu 2026-08-15):
        araba / arabayla -> "araba" / "araba"   (esit)
        ev    / evde     -> "ev"    / "evde"    (onek)
        su    / sular    -> "su"    / "sular"   (onek)
    """
    w = (word or "").strip().lower()
    if not w:
        return ""
    for inf in _INFINITIVE_SUFFIXES:
        if w.endswith(inf) and len(w) - len(inf) >= _MIN_STEM_LEN:
            return w[: -len(inf)]
    for suffix in sorted(_MATCH_SUFFIXES, key=len, reverse=True):
        if w.endswith(suffix) and len(w) - len(suffix) >= _MIN_STEM_LEN:
            return w[: -len(suffix)]
    return w
