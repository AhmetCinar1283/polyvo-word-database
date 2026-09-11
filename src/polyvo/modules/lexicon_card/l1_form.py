"""
L1 karsiliginin dil + sozluk-bicimi kapisi — TEK tanim yeri.

Tek cagirani `translate/qa/gloss.py`dir — dort dil de ayni
kapidan gecsin diye burada durur. Kart QA'si L1'e HIC bakmaz: odenmis bir
Ingilizce kart, cevirisi yuzunden reddedilemez.

KAPI IKI SEY DONER: red sebebi VE uyari. Ayrim §6.7'nin kuralidir — garanti
edilemeyen kontrol REDDETMEZ, uyarir. Burada iki yerde uygulanir:

1. Dil isaretci kapisi ("model cevirmeyip Ingilizce'yi mi dondurdu")
   yalnizca UZUN cevapta reddeder. OLCULDU (es pilotu, 2026-09-06): tek
   kelimelik islev sozcuklerinde ayirt etme gucu SIFIR — `non`->"no",
   `to`->"a" DOGRU Ispanyolca cevaplardi ve ucu de reddedildi, uc birim icin
   6 cagri odenip hepsi kaybedildi (yeniden deneme ayni dogru cevabi uretip
   ayni duvara carpiyor).
2. `check_form`un `SOFT_FORM_CODES`ta ilan edilen kodlari uyariya dusurulur
   (bkz. `core/lang/tr.py::looks_conjugated`).
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.core.lang import get_rules
from polyvo.modules.lexicon_card import l1_language

#: Dil isaretci kapisi bu KELIME SAYISININ altinda reddetmez, uyarir.
#: Kisa karsilikta Ispanyolca "no"/"a" ile Ingilizce "no"/"a" ayni harfleri
#: kullanir; sinyal ancak birkac kelimede anlam kazanir.
MIN_WORDS_FOR_LANG_GATE = 3


@dataclass(frozen=True)
class FormResult:
    """Kapinin sonucu: red sebebi (varsa) ve reddetmeyen uyarilar."""

    reject: str | None = None
    warnings: tuple[str, ...] = ()


def check(gloss_l1: str, pos: str, l1: str) -> FormResult:
    """L1 karsiliginin dili ve sozluk bicimi kapisi."""
    rules = get_rules(l1)
    warnings: list[str] = []

    # Model cevirmeyip Ingilizce'yi aynen geri dondurmus mu?
    if l1_language.looks_english_not_l1(gloss_l1, l1):
        if len(gloss_l1.split()) >= MIN_WORDS_FOR_LANG_GATE:
            return FormResult(reject="l1_ceviri_yapilmamis")
        warnings.append("l1_ceviri_supheli_kisa_karsilik")

    code = rules.check_form(pos, gloss_l1)
    if code:
        if code in rules.SOFT_FORM_CODES:
            warnings.append(code)
        else:
            return FormResult(reject=code, warnings=tuple(warnings))

    return FormResult(warnings=tuple(warnings))
