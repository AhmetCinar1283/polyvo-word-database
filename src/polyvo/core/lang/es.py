"""
Ispanyolca (L1) bicim kurallari — sozluk bicimi kapisi (`check_form`).

Tek gercek kontrol: FIIL MASTARI. Ispanyolca fiil mastarlari `-ar/-er/-ir`
(donusluler `-arse/-erse/-irse`) ile biter; model cekimli bicim ("corre")
ya da Ingilizce mastar ("to run") donebilir — ikisi de burada yakalanir.
Isim/sifat bicimi icin GUVENILIR bir kural yok (cinsiyet/coğul eki
belirsiz), bu yuzden kapi yapilmadi (`tr.py`'nin dedigi gibi, emin
olunmayan kontrol reddetmez).
"""

LANGUAGE_NAME = "Spanish"

_INFINITIVE_SUFFIXES = ("ar", "er", "ir", "arse", "erse", "irse")

PROMPT_RULES = (
    "- Spanish verbs MUST be given in the infinitive, ending in \"-ar\", \"-er\" "
    "or \"-ir\" (e.g. \"correr\", \"comer\" — NOT \"corre\", \"to run\").\n"
    "- Nouns/adjectives/adverbs MUST be in the bare dictionary form: singular, "
    "no article (\"el\"/\"la\"/\"los\"/\"las\")."
)

REVIEW_RULES = (
    "- pos='verb' ise karşılık MUTLAKA İspanyolca mastar halinde olmalı "
    "(-ar/-er/-ir): \"correr\" DOĞRU, \"corre\"/\"corriendo\"/\"to run\" YANLIŞ.\n"
    "- pos noun/adj/adv ise tekil, artikelsiz temel biçim olmalı."
)


def check_form(part_of_speech: str, text: str) -> str | None:
    """Ispanyolca sozluk bicimi kapisi. Sorun varsa kisa kod, yoksa None."""
    if not text:
        return None
    tail = text.strip().lower().split()[-1] if text.strip() else ""
    if not tail:
        return None
    if part_of_speech == "verb" and not tail.endswith(_INFINITIVE_SUFFIXES):
        return "verb_missing_infinitive"
    return None


# Ingilizce'yle CAKISMAYAN ucuz sinyaller: aksanli harfler + Ingilizce'de
# GECMEYEN yaygin islev kelimeleri. Model cevirmeyip Ingilizce'yi aynen geri
# donerse bu kapiyla yakalanir. Ingilizce'de DE gecen kelime buraya KONMAZ,
# `ENGLISH_AMBIGUOUS`a konur.
#
# IGNORECASE ACIK (2026-09-07 duzeltmesi): kapali oldugu icin cumle BASINDAKI
# "El"/"Una"/"Como" sayilmiyordu. Isaretcinin YOKLUGU red anlamina geldiginden
# buyuk/kucuk harf duyarliligi yanlis alarmi azaltmiyor, ARTIRIYORDU.
import re as _re  # noqa: E402

LANG_MARKERS = _re.compile(
    r"[ñáéíóúü¿¡]"
    r"|(?i:\b(el|la|los|las|de|del|que|con|para|pero|más|muy|una|uno|"
    r"como|cuando|donde|también|esta|este|esos|esas|en|es|son|se|su|sus|"
    r"al|lo|le|les|ni|sin|sobre|hasta|desde|entre|algo|alguien|ser|está|"
    r"están|hacer|cada|todo|todos|otro|otra|puede|tener|porque|aunque|"
    r"siempre|nunca|ahora|persona|personas|cosa|cosas)\b)"
)

# Ingilizce isaretcisi olup ISPANYOLCA'da da gecen kelimeler — Ingilizce
# KANITI SAYILMAZ (bkz. `core/text/qa.py::english_marker_hits`). OLCULDU
# (2026-09-07): "...relativo a algo" ve "No estoy cansado..." gibi DOGRU
# cevirileri reddettiren tek sebep buradaki `a`/`no` idi.
ENGLISH_AMBIGUOUS = frozenset({"a", "no", "me", "he", "ve"})

# Bu dilde terim tutarliligi kapisi (kok BASTA kalir varsayimi) acilmadi:
# Ispanyolca'da on ek/artikel yaygin, olcum yapilmadan guvenilmez.
TERM_MATCH_SUPPORTED = False
