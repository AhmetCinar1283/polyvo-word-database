"""
Turkce (L1) bicim kurallari — sozluk bicimi kapisi (`check_form`) + gevsek
kok eslestirme (`stem_for_match`). Diger diller bu kurallardan etkilenmez;
yeni dil eklerken bu dosya ornek alinir.

BULGU: LLM TR karsiliklarinin ~%12-15'i sessizce yanlis; yarisi FIIL MASTAR
HATASI (model "unutmak" yerine "unut" doner) — `check_form` bunu yakalar.
Kalan yari saf anlam hatasi, yalnizca insan denetimiyle (`review.py`) yakalanir.
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
    Cok kelimeli ifadede SON kelimeye bakilir (Turkce'de bas sondadir)."""
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


# Metnin gercekten Turkce oldugunu gosteren ucuz sinyaller (ozgu harfler ya
# da yaygin islev kelimeleri) — model cevirmeyip Ingilizce'yi aynen geri
# donerse bu kapiyla yakalanir.
import re as _re  # noqa: E402  (modul sonunda, ustteki saf-veri blogunu bozmamak icin)

# `re.IGNORECASE` bu desende KULLANILMAZ: Python'da 'ı'.upper()=='I' oldugu
# icin IGNORECASE altinda 'ı' ASCII 'i' ile eslesip her "i" gecen Ingilizce
# cumleyi Turkce sanardi. Kelime listesinde de Ingilizce'yle cakisan
# "her"/buyuk "I" YOK — ikisi de gercek Ingilizce'de sik gecer.
LANG_MARKERS = _re.compile(
    r"[çğıöşüÇĞİÖŞÜ]"
    r"|(?i:\b(bir|ve|bu|şu|için|ile|olarak|daha|çok|ama|gibi|kadar|"
    r"sonra|önce|olan|değil|yok|mi|mı|degil|icin|cok)\b)"
)

# Terim tutarliligi kapisi SADECE bu bayragi acan dillerde calisir: altindaki
# karsilastirma "kok BASTA kalir, ekler SONA gelir" varsayar — Turkce'de
# dogru, on-ekli dillerde (Almanca, Rusca) degil. Yeni L1 eklerken once olcum yap.
TERM_MATCH_SUPPORTED = True

# Kok eslestirme icin soyulacak ekler (en uzun eslesen BIR kez soyulur) —
# tam morfoloji DEGIL, sadece "araba"/"arabayla" ayni sozcuk mu sorusu.
# TEK HARFLI ekler BILEREK yok: "araba"->"arab" gibi kok bozan asiri-soyma
# yanlis alarm uretir, az soymak (kacirmak) tercih edilir.
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
    """Gevsek Turkce kok — SADECE metin ici arama karsilastirmasi icin (iki
    yuzey bicim ayni sozcuk mu). Cagiran taraf IKI YONLU ONEK iliskisiyle
    karsilastirmali: `a.startswith(b) or b.startswith(a)`."""
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
