"""
Brezilya Portekizcesi (L1) bicim kurallari — sozluk bicimi kapisi
(`check_form`). Depoda/konfigde dil kodu tireli (`pt-BR`) tasinir;
`core/lang/__init__.py::get_rules` modul adini `pt_br`e normalize eder.

Tek gercek kontrol: FIIL MASTARI. Portekizce fiil mastarlari `-ar/-er/-ir/-or`
ile biter; model cekimli bicim ("corre") ya da Ingilizce mastar ("to run")
donebilir — ikisi de burada yakalanir.
"""

LANGUAGE_NAME = "Brazilian Portuguese"

_INFINITIVE_SUFFIXES = ("ar", "er", "ir", "or")

PROMPT_RULES = (
    "- Portuguese (Brazilian) verbs MUST be given in the infinitive, ending "
    "in \"-ar\", \"-er\", \"-ir\" or \"-or\" (e.g. \"correr\", \"comer\" — "
    "NOT \"corre\", \"to run\").\n"
    "- Nouns/adjectives/adverbs MUST be in the bare dictionary form: "
    "singular, no article (\"o\"/\"a\"/\"os\"/\"as\")."
)

REVIEW_RULES = (
    "- pos='verb' ise karşılık MUTLAKA Portekizce (BR) mastar halinde olmalı "
    "(-ar/-er/-ir/-or): \"correr\" DOĞRU, \"corre\"/\"correndo\"/\"to run\" "
    "YANLIŞ.\n"
    "- pos noun/adj/adv ise tekil, artikelsiz temel biçim olmalı."
)


def check_form(part_of_speech: str, text: str) -> str | None:
    """Portekizce (BR) sozluk bicimi kapisi. Sorun varsa kisa kod, yoksa None."""
    if not text:
        return None
    tail = text.strip().lower().split()[-1] if text.strip() else ""
    if not tail:
        return None
    if part_of_speech == "verb" and not tail.endswith(_INFINITIVE_SUFFIXES):
        return "verb_missing_infinitive"
    return None


# Ingilizce'yle CAKISMAYAN ucuz sinyaller: aksanli/nazal harfler + Ingilizce'de
# GECMEYEN yaygin islev kelimeleri. Ingilizce'de DE gecen kelime (`a`, `as`,
# `do`, `no`) buraya KONMAZ — `ENGLISH_AMBIGUOUS`a konur. IGNORECASE icin
# es.py'deki 2026-09-07 gerekcesi aynen gecerli.
import re as _re  # noqa: E402

LANG_MARKERS = _re.compile(
    r"[ãõçáéíóúâêô]"
    r"|(?i:\b(não|com|para|mas|muito|uma|um|como|quando|onde|também|"
    r"está|esse|essa|esses|essas|isso|então|de|da|das|dos|que|em|por|ao|"
    r"aos|na|nas|nos|seu|sua|seus|suas|ser|são|estão|pelo|pela|sem|sobre|"
    r"até|ainda|cada|todo|todos|outro|outra|algo|alguém|ou|mais|quem|"
    r"foi|era|tem|pessoa|pessoas|coisa|coisas)\b)"
)

# Ingilizce isaretcisi olup PORTEKIZCE'de de gecen kelimeler — Ingilizce
# KANITI SAYILMAZ. OLCULDU (2026-09-07): "A loja vende..." ve "A autora
# publicou... no ano passado." DOGRU cevirilerdi, `a`/`no` yuzunden reddedildi.
ENGLISH_AMBIGUOUS = frozenset({"a", "as", "do", "no", "me", "so"})

# Bu dilde terim tutarliligi kapisi acilmadi — Portekizce'de on ek/artikel
# yaygin, olcum yapilmadan guvenilmez.
TERM_MATCH_SUPPORTED = False
