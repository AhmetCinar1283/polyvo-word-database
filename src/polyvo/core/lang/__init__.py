"""
Dile ozgu kurallarin TEK toplandigi eklenti kaydi — her dil modulu
(`tr.py`, `es.py`, ileride baskalari...) izole kalir, digerlerini etkilemez.

Her modulun saglayacagi arayuz: `LANGUAGE_NAME`, `check_form(pos, text)`
(sozluk bicimi kapisi), `SOFT_FORM_CODES` (check_form'un REDDETMEYEN,
yalnizca UYARAN kodlari), `PROMPT_RULES`, `REVIEW_RULES`, `LANG_MARKERS`
(dil tespiti, istege bagli), `ENGLISH_AMBIGUOUS` (bu dilde DE gecen, bu
yuzden Ingilizce kaniti SAYILMAYAN isaretciler), `stem_for_match` (gevsek
kok, istege bagli).

`LANG_MARKERS` ile `ENGLISH_AMBIGUOUS` ayni madalyonun iki yuzudur ve
birlikte bakilmalidir: birincisi "Ingilizce'de GECMEYEN L1 kelimeleri",
ikincisi "L1'de DE gecen Ingilizce kelimeleri". Bir kelime ikisine birden
konulmaz — bir dilde de bir dilde de geceni kanit saymak kapiyi bozar.

Kural modulu OLMAYAN dil sorunsuz calisir: `get_rules()` no-op varsayilan
doner — yeni bir L1 once kuralsiz baslar, gerekirse modulu sonra yazilir.

TUZAK: `pt-BR` gibi tireli kodlar gecerli bir Python modul adi degildir.
Modul ADI burada normalize edilir (tire -> alt cizgi, kucuk harf); onbellek
ve `LANGUAGE_NAME` aramasi ise HAM kod (`pt-BR`) ile yapilir. Modul GERCEKTEN
var ama BOZUKSA (kendi ici bir import hatasi) bu sessizce yutulmaz — yalnizca
aranan modulun kendisi YOK ise no-op varsayilana dusulur.
"""

import importlib
from types import SimpleNamespace

from polyvo.core.paths import language_name

_DEFAULT = SimpleNamespace(
    LANGUAGE_NAME="",
    PROMPT_RULES="",
    REVIEW_RULES="",
    LANG_MARKERS=None,
    # Ingilizce isaretcisi olup bu dilde DE gecen kelimeler: Ingilizce kaniti
    # SAYILMAZ (bkz. `core/text/qa.py::english_marker_hits`).
    ENGLISH_AMBIGUOUS=frozenset(),
    check_form=lambda part_of_speech, text: None,
    # `check_form` bir kod dondurse bile BURADAKILER reddetmez, uyarir —
    # garanti edilemeyen kontrolun yeri budur (§6.7).
    SOFT_FORM_CODES=frozenset(),
    stem_for_match=lambda word: (word or "").strip().lower(),
)

_cache: dict[str, object] = {}


def _module_name(lang: str) -> str:
    """`lang` kodunu gecerli bir Python modul adina cevirir (`pt-BR` -> `pt_br`)."""
    return lang.replace("-", "_").lower()


def get_rules(lang: str):
    """`lang` icin kural modulunu doner; yoksa no-op varsayilan. Eksik
    arayuz uyeleri varsayilanla tamamlanir (cagiran `getattr` yazmasin diye)."""
    if lang in _cache:
        return _cache[lang]

    target = _module_name(lang)
    try:
        module = importlib.import_module(f"polyvo.core.lang.{target}")
    except ModuleNotFoundError as exc:
        # Yalnizca ARANAN modulun KENDISI yoksa no-op'a dus. Modul VAR ama
        # kendi ici bir bagimliligi eksikse (`exc.name` baska bir paket),
        # bu YUTULMAZ — deponun "import hatasi asla sessizce yenilmez"
        # disiplini burada da gecerli.
        if exc.name != f"polyvo.core.lang.{target}":
            raise
        module = SimpleNamespace(
            LANGUAGE_NAME=language_name(lang),
            PROMPT_RULES=_DEFAULT.PROMPT_RULES,
            REVIEW_RULES=_DEFAULT.REVIEW_RULES,
            LANG_MARKERS=_DEFAULT.LANG_MARKERS,
            ENGLISH_AMBIGUOUS=_DEFAULT.ENGLISH_AMBIGUOUS,
            check_form=_DEFAULT.check_form,
            SOFT_FORM_CODES=_DEFAULT.SOFT_FORM_CODES,
            stem_for_match=_DEFAULT.stem_for_match,
        )
    else:
        for member, fallback in vars(_DEFAULT).items():
            if not hasattr(module, member):
                setattr(module, member, fallback)
    _cache[lang] = module
    return module
