"""
Dile ozgu kurallarin TEK toplandigi eklenti kaydi — her dil modulu
(`tr.py`, ileride `es.py`...) izole kalir, digerlerini etkilemez.

Her modulun saglayacagi arayuz: `LANGUAGE_NAME`, `check_form(pos, text)`
(sozluk bicimi kapisi), `PROMPT_RULES`, `REVIEW_RULES`, `LANG_MARKERS`
(dil tespiti, istege bagli), `stem_for_match` (gevsek kok, istege bagli).

Kural modulu OLMAYAN dil sorunsuz calisir: `get_rules()` no-op varsayilan
doner — yeni bir L1 once kuralsiz baslar, gerekirse modulu sonra yazilir.
"""

import importlib
from types import SimpleNamespace

from polyvo.core.paths import language_name

_DEFAULT = SimpleNamespace(
    LANGUAGE_NAME="",
    PROMPT_RULES="",
    REVIEW_RULES="",
    LANG_MARKERS=None,
    check_form=lambda part_of_speech, text: None,
    stem_for_match=lambda word: (word or "").strip().lower(),
)

_cache: dict[str, object] = {}


def get_rules(lang: str):
    """`lang` icin kural modulunu doner; yoksa no-op varsayilan. Eksik
    arayuz uyeleri varsayilanla tamamlanir (cagiran `getattr` yazmasin diye)."""
    if lang in _cache:
        return _cache[lang]
    try:
        module = importlib.import_module(f"polyvo.core.lang.{lang}")
    except ModuleNotFoundError:
        module = SimpleNamespace(
            LANGUAGE_NAME=language_name(lang),
            PROMPT_RULES=_DEFAULT.PROMPT_RULES,
            REVIEW_RULES=_DEFAULT.REVIEW_RULES,
            LANG_MARKERS=_DEFAULT.LANG_MARKERS,
            check_form=_DEFAULT.check_form,
            stem_for_match=_DEFAULT.stem_for_match,
        )
    else:
        for member, fallback in vars(_DEFAULT).items():
            if not hasattr(module, member):
                setattr(module, member, fallback)
    _cache[lang] = module
    return module
