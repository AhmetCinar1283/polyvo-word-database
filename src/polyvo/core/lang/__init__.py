"""
Dile ozgu kurallarin TEK toplandigi eklenti kaydi.

NEDEN VAR: onceki surumde Turkce morfoloji kurallari (`-mek/-mak` mastar
zorunlulugu, `_CONJUGATED_SUFFIXES` cekim eki listesi) dogrudan
`tr_gloss.py`'nin govdesine gomuluydu. Bu blok tek basina escalation
kuyrugunun ~%28'ini uretiyordu — yani silinemeyecek kadar degerli, ama
Ispanyolca/Almanca/Rusca icin tamamen anlamsiz. Cozum: kurallari silmek de
genellestirmeye calismak da degil, IZOLE ETMEK.

Her dil modulu (`tr.py`, ileride `es.py`, `de.py`...) su arayuzu saglar:

    LANGUAGE_NAME: str
        Prompt metinlerinde kullanilacak Ingilizce dil adi.

    check_form(part_of_speech: str, text: str) -> str | None
        Ceviri metni o dilin beklenen SOZLUK BICIMINDE mi? Sorun varsa
        kisa bir kod doner (orn. "verb_missing_infinitive"), yoksa None.
        Bu ucuz/sezgisel bir kapidir — LLM'in kendi guveni ve insan
        denetimi ile birlikte cok katmanli calisir, tek basina karar vermez.

    PROMPT_RULES: str
        Uretim prompt'una eklenecek, o dile ozgu bicim kurallari
        (orn. "verbs MUST be in the infinitive, ending -mek/-mak").

    REVIEW_RULES: str
        `review.py`'nin export dosyasina yazacagi, kullanicinin harici
        sohbete yapistiracagi talimat blogundaki dile ozgu maddeler.

    LANG_MARKERS: re.Pattern | None            (F6, istege bagli)
        Metnin gercekten O DILDE oldugunu gosteren ucuz bir duzenli ifade.
        None ise ceviri dil kapisi o dil icin ATLANIR.

    stem_for_match(word: str) -> str           (F6, istege bagli)
        Metin ici karsilastirma icin gevsek kok. Varsayilani birim
        fonksiyondur (kelimeyi oldugu gibi doner), yani terim tutarliligi
        kapisi kurali olmayan dilde sadece TAM eslesmeye bakar.

Kural modulu OLMAYAN bir dil sorunsuz calisir: `get_rules()` no-op bir
varsayilan doner (hicbir bicim uyarisi uretmez, prompt'a ek madde koymaz).
Yani yeni bir L1 eklemek once kuralsiz baslar, ihtiyac gorulurse o dilin
modulu sonradan yazilir.
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
    """`lang` icin kural modulunu doner; yoksa no-op varsayilan.

    Var olan bir modul YENI arayuz uyelerini (orn. F6'nin `LANG_MARKERS`'i)
    tanimlamamis olabilir — o durumda da cagiran taraf `getattr` yazmak
    zorunda kalmasin diye eksik uyeler varsayilanla tamamlanir.
    """
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
