"""
`core/lang` testleri — dil kural kaydinin sozlesmesi.

Iki tuzak burada denetlenir: (1) `pt-BR` gibi tireli kodlarin modul
aramasinda SESSIZCE kuralsiza dusmemesi; (2) VAR OLAN ama bozuk bir dil
modulunun (kendi ici bir import hatasi) yine SESSIZCE yutulmamasi.
Ayrica her yeni dilin `check_form`u en az bir gercek hatayi yakaladigini
ve dogru bicimi reddetmedigini gosterir.
"""

from __future__ import annotations

import sys
import types

import pytest

from polyvo.core.lang import get_rules


def test_pt_br_tireli_kod_kural_modulunu_bulur():
    rules = get_rules("pt-BR")
    assert rules.LANGUAGE_NAME == "Brazilian Portuguese"
    # No-op varsayilanin PROMPT_RULES'u BOS'tur; gercek modulde DOLU olmali.
    assert rules.PROMPT_RULES


def test_bilinmeyen_dil_no_op_varsayilana_duser():
    rules = get_rules("xx-yok-boyle-dil")
    assert rules.PROMPT_RULES == ""
    assert rules.check_form("verb", "anything") is None


def test_bozuk_dil_modulu_sessizce_yutulmaz(monkeypatch):
    """Modul VAR ama kendi ici bir bagimliligi eksikse hata YUKARI cikmali."""
    from polyvo.core.lang import _cache

    broken = types.ModuleType("polyvo.core.lang.zz")

    def _raise_import():
        raise ModuleNotFoundError("bu-paket-hic-yok", name="bu-paket-hic-yok")

    # Gercek importlib.import_module'u, hedef modul icin bozuk bir zincire
    # yonlendiriyoruz: `exc.name` aranan modulden FARKLI olacak.
    import importlib as importlib_mod
    real_import_module = importlib_mod.import_module

    def fake_import_module(name):
        if name == "polyvo.core.lang.zz":
            _raise_import()
        return real_import_module(name)

    monkeypatch.setattr(importlib_mod, "import_module", fake_import_module)
    monkeypatch.setattr("polyvo.core.lang.importlib.import_module",
                        fake_import_module)
    _cache.pop("zz", None)
    with pytest.raises(ModuleNotFoundError):
        get_rules("zz")
    _cache.pop("zz", None)


@pytest.mark.parametrize("lang,bad,good", [
    ("es", "corre", "correr"),
    ("pt-BR", "corre", "correr"),
    ("de", "läuft", "laufen"),
    ("tr", "koşuyor", "koşmak"),
])
def test_yeni_dillerde_fiil_mastari_kapisi(lang, bad, good):
    rules = get_rules(lang)
    assert rules.check_form("verb", bad) is not None
    assert rules.check_form("verb", good) is None


def test_almanca_isim_buyuk_harf_kapisi():
    rules = get_rules("de")
    assert rules.check_form("noun", "haus") == "noun_not_capitalized"
    assert rules.check_form("noun", "Haus") is None


@pytest.mark.parametrize("lang", ["es", "pt-BR", "de", "tr"])
def test_lang_markers_ingilizce_donusu_yakalar(lang):
    rules = get_rules(lang)
    from polyvo.core.text import qa as text_qa

    # Model cevirmeyip Ingilizce'yi aynen geri dondurmus — LANG_MARKERS
    # eslesmez ama AYIRT EDICI Ingilizce isaretcisi bulunur.
    assert rules.LANG_MARKERS.search("to run fast") is None
    assert text_qa.english_marker_hits("to run fast", rules.ENGLISH_AMBIGUOUS) > 0


# --- Dil isaretci kapisinin iki yuzu (2026-09-07 yanlis-red duzeltmesi) ----

@pytest.mark.parametrize("lang,cumle_basi", [
    ("es", "Una persona que trabaja"),
    ("pt-BR", "Uma pessoa que trabalha"),
    ("de", "Eine Person, der man vertraut"),
    ("tr", "Bir kimse"),
])
def test_lang_markers_cumle_basindaki_buyuk_harfi_de_sayar(lang, cumle_basi):
    """Isaretcinin YOKLUGU red anlamina geldigi icin buyuk/kucuk harf
    duyarliligi yanlis alarmi AZALTMAZ, ARTIRIR. Olculdu: kapali IGNORECASE
    yuzunden "Eine Person..." Almanca sayilmiyordu."""
    assert get_rules(lang).LANG_MARKERS.search(cumle_basi) is not None


@pytest.mark.parametrize("lang", ["es", "pt-BR", "de", "tr"])
def test_bir_kelime_iki_listede_birden_olamaz(lang):
    """Sozlesme: `LANG_MARKERS` = "Ingilizce'de gecmeyen L1 kelimeleri",
    `ENGLISH_AMBIGUOUS` = "L1'de de gecen Ingilizce kelimeleri". Ayni kelime
    ikisinde birden olursa kapi hem "L1'dir" hem "kanit sayilmaz" der —
    isaretci kumesi anlamini kaybeder."""
    rules = get_rules(lang)
    cakisan = {w for w in rules.ENGLISH_AMBIGUOUS
               if rules.LANG_MARKERS.fullmatch(w)}
    assert not cakisan, cakisan


@pytest.mark.parametrize("lang", ["es", "pt-BR", "de", "tr"])
def test_ambigu_isaretciler_gercekten_ingilizce_isaretcisidir(lang):
    """`ENGLISH_AMBIGUOUS`a `ENGLISH_MARKERS`ta OLMAYAN bir kelime yazmak
    sessiz bir no-op'tur — yazan kisi bir seyi engelledigini sanir."""
    from polyvo.core.text import qa as text_qa

    for word in get_rules(lang).ENGLISH_AMBIGUOUS:
        assert text_qa.ENGLISH_MARKERS.fullmatch(word), word


# --- SOFT_FORM_CODES sozlesmesi -------------------------------------------

def test_kural_modulu_olmayan_dilde_soft_kod_kumesi_bostur():
    """Arayuzun yeni uyesi eksik dilde de tanimli olmali — cagiran taraf
    `getattr` yazmasin (kayit sozlesmesinin kurali)."""
    assert get_rules("xx-yok-boyle-dil").SOFT_FORM_CODES == frozenset()


def test_tr_looks_conjugated_reddetmeyen_kod_olarak_ilan_edilmis():
    """`check_form` kodu uretmeye devam eder (iz kalsin), ama bu kod
    REDDETMEZ — olculdu, neredeyse hepsi yanlis alarmdi."""
    rules = get_rules("tr")
    assert rules.check_form("noun", "kutu") == "looks_conjugated"
    assert "looks_conjugated" in rules.SOFT_FORM_CODES
    # Fiil kapisi yumusatilmadi: o olculdu ve dogru calisiyor.
    assert "verb_missing_infinitive" not in rules.SOFT_FORM_CODES
