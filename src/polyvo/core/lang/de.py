"""
Almanca (L1) bicim kurallari — sozluk bicimi kapisi (`check_form`).

Iki gercek kontrol: (1) FIIL MASTARI `-en`/`-n` ile biter (model cekimli
bicim ya da Ingilizce mastar donebilir); (2) ISIMLER BUYUK HARFLE BASLAR —
Almanca yazim kuralinin bir parcasi, ucuz ve guvenilir bir kontrol.
"""

LANGUAGE_NAME = "German"

_INFINITIVE_SUFFIXES = ("en", "n")

PROMPT_RULES = (
    "- German verbs MUST be given in the infinitive, ending in \"-en\" or "
    "\"-n\" (e.g. \"laufen\", \"sammeln\" — NOT \"läuft\", \"to run\").\n"
    "- German nouns MUST start with a capital letter (e.g. \"Haus\", not "
    "\"haus\"), with no article (\"der\"/\"die\"/\"das\")."
)

REVIEW_RULES = (
    "- pos='verb' ise karşılık MUTLAKA Almanca mastar halinde olmalı "
    "(-en/-n): \"laufen\" DOĞRU, \"läuft\"/\"to run\" YANLIŞ.\n"
    "- pos='noun' ise karşılık BÜYÜK HARFLE başlamalı: \"Haus\" DOĞRU, "
    "\"haus\" YANLIŞ."
)


def check_form(part_of_speech: str, text: str) -> str | None:
    """Almanca sozluk bicimi kapisi. Sorun varsa kisa kod, yoksa None."""
    if not text:
        return None
    stripped = text.strip()
    tail = stripped.lower().split()[-1] if stripped else ""
    if not tail:
        return None

    if part_of_speech == "verb" and not tail.endswith(_INFINITIVE_SUFFIXES):
        return "verb_missing_infinitive"

    if part_of_speech == "noun":
        first_word = stripped.split()[0]
        if not first_word[:1].isupper():
            return "noun_not_capitalized"

    return None


# Ingilizce'yle CAKISMAYAN ucuz sinyaller: umlaut/ß + Ingilizce'de GECMEYEN
# yaygin islev kelimeleri. Ingilizce'de DE gecen kelime (`in`, `so`, `man`,
# `war`, `was`, `will`) buraya KONMAZ — bir kismi `ENGLISH_AMBIGUOUS`a girer,
# gerisi hic sayilmaz. Ayni sebeple `die` de YOK: Ingilizce bir fiildir,
# cevrilmemis Ingilizce metni Almanca sanmaya yol acardi (Almanca cumlede
# `der`/`das`/`ist`/`zu` zaten neredeyse her zaman bulunur).
#
# IGNORECASE ACIK (2026-09-07 duzeltmesi): kapali oldugu icin cumle BASINDAKI
# "Eine"/"Der" sayilmiyordu ve isaretcinin YOKLUGU red demekti.
import re as _re  # noqa: E402

LANG_MARKERS = _re.compile(
    r"[äöüßÄÖÜ]"
    r"|(?i:\b(und|nicht|mit|für|aber|sehr|eine|ein|wie|wenn|wo|auch|"
    r"dieser|diese|dieses|dann|oder|kein|keine|der|das|den|dem|des|"
    r"einen|einem|einer|eines|ist|sind|zu|auf|von|im|vom|zum|zur|"
    r"dass|als|nach|bei|nur|noch|sich|sein|seine|ihr|ihre|werden|wird|"
    r"wurde|haben|hat|hatte|kann|etwas|alle|viele|jemand|menschen)\b)"
)

# Ingilizce isaretcisi olup ALMANCA'da da gecen kelimeler — Ingilizce KANITI
# SAYILMAZ. OLCULDU (2026-09-07): "in der Lage sein, etwas zu tun" ve
# "Eine Person, die die Dienste eines Profis in Anspruch nimmt." DOGRU
# cevirilerdi; ikisini de reddettiren tek kanit `in` idi.
ENGLISH_AMBIGUOUS = frozenset({"in", "so", "am", "an", "will", "was",
                               "her", "also"})

# Bu dilde terim tutarliligi kapisi acilmadi — Almanca ON EKLI (be-, ver-,
# ge- vb.) bir dil, "kok BASTA kalir" varsayimi burada gecersiz.
TERM_MATCH_SUPPORTED = False
