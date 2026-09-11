"""
Cloze QA testleri — RED ile UYARI ayrimini civiler.

Bu isin en buyuk kalite riski "celdirici gercekten uymuyor mu" sorusunun
olculememesidir. Buradaki testler iki seyi birden gosterir: olculebilen sey
REDDEDER, olculemeyen sey UYARIR ve satiri cope ATMAZ.

Hicbir ag cagrisi yok; gercek QA saf bir `Unit` uzerinde calisir.
"""

from __future__ import annotations

import copy

import pytest

from cloze_helpers import TAG, cloze_answer, seed_build_cefr
from polyvo.core import paths
from polyvo.core.jobs.base import Unit
from polyvo.dictionary.build import stages as dict_stages
from polyvo.modules.cloze import cefr, render, scene
from polyvo.modules.cloze.qa import run
from polyvo.modules.cloze.qa.variety import opening_ngram


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))
    seed_build_cefr()


def _unit(cefr="A2", headword="bank", pos="noun") -> Unit:
    """QA'nin bekledigi alanlari tasiyan sahte birim."""
    key = f"en:{headword}:{pos}"
    return Unit(key=key, name=headword, data={
        "stable_key": key, "sense_id": 1, "item_id": 1, "headword": headword,
        "pos": pos, "cefr": cefr, "cefr_db": dict_stages.lexicon_db_path(TAG),
        "card": {"gloss_en": "A place where money is kept.",
                 "register": "neutral", "examples": ["I went to the bank."]}})


def _broken(mutate, **unit_kwargs):
    """Gecerli cevabi bozup QA'dan gecirir; sonucu doner."""
    answer = copy.deepcopy(cloze_answer())
    mutate(answer)
    return run(answer, _unit(**unit_kwargs))


# --- Gecerli paket ---------------------------------------------------------

def test_gecerli_paket_onaylanir_ama_uyarisiz_degildir():
    """Dogru bir paket gecer; yine de celdirici uyarisi TASIR — QA'nin
    olcemedigi sey sessizce 'temiz' gorunmemeli."""
    result = run(cloze_answer(), _unit())
    assert result.ok
    assert "celdiricinin_uymadigi_dogrulanamadi" in result.reason


# --- Bicim kapilari (REDDEDER) ---------------------------------------------

@pytest.mark.parametrize("mutate, expected", [
    (lambda a: a["questions"].pop(), "soru_sayisi_uc_degil"),
    (lambda a: a["questions"][0].update(options=["bank", "spoon", "cloud"]),
     "sik_sayisi_dort_degil"),
    (lambda a: a["questions"][0].update(options=["bank", "bank", "cloud", "chair"]),
     "siklar_birbirinin_aynisi"),
    (lambda a: a["questions"][0].update(answer="vault"),
     "dogru_cevap_siklar_arasinda_yok"),
    (lambda a: a["questions"][1].update(difficulty="zor"),
     "zorluk_etiketi_sirayla_uyusmuyor"),
])
def test_bicim_hatalari_reddedilir(mutate, expected):
    """Sayilabilir her bicim hatasi REDDEDER — garanti edilebilir."""
    assert _broken(mutate).reason == expected


def test_uc_soru_dort_sik_tek_dogru_cevap_yazilir():
    """Onayli yukte tam 3 soru, her birinde tam 4 sik ve tek dogru cevap."""
    payload = run(cloze_answer(), _unit()).payload
    assert len(payload["questions"]) == 3
    for question in payload["questions"]:
        assert len(question["options"]) == 4
        assert sum(1 for o in question["options"]
                   if o.lower() == question["answer"].lower()) == 1


# --- Bosluk kapilari (REDDEDER) --------------------------------------------

def test_hedef_kelime_yoksa_reddedilir():
    """Doldurulacak bosluk yoksa soru da yoktur."""
    assert _broken(lambda a: a["questions"][0].update(
        sentence="I keep my money in a box.")).reason == "hedef_kelime_cumlede_yok"


def test_hedef_kelime_iki_kez_gecerse_reddedilir():
    """Iki kez gecerse boslugun hangi gecisten olustugu belirsizdir."""
    assert _broken(lambda a: a["questions"][0].update(
        sentence="The bank is a bank.")).reason == \
        "hedef_kelime_cumlede_birden_cok_kez"


def test_dogru_cevap_cumledeki_bicim_degilse_reddedilir():
    """Sik "banks" ise cumledeki "bank" boslugu ona uymaz."""
    assert _broken(lambda a: a["questions"][0].update(
        answer="banks", options=["banks", "spoon", "cloud", "chair"])).reason == \
        "dogru_cevap_cumledeki_bicim_degil"


# --- Celdirici kapilari ----------------------------------------------------

def test_hedefin_cekimini_celdirici_yapan_cevap_reddedilir():
    """Kabul olcutu: hedef kelimenin kendisi/cekimi celdirici OLAMAZ —
    ogrenciye bedava eleme verir."""
    assert _broken(lambda a: a["questions"][0].update(
        options=["bank", "banks", "cloud", "chair"])).reason == \
        "celdirici_hedef_kelimenin_bicimi"


def test_celdiricinin_sozcuk_turu_farkliysa_reddedilir():
    """Zarf, isim boslugunda bedava elenir — soruyu kolaylastirir."""
    assert _broken(lambda a: a["questions"][0].update(
        options=["bank", "quickly", "cloud", "chair"])).reason == \
        "celdirici_sozcuk_turu_farkli"


def test_celdirici_cefri_hedefin_ustundeyse_reddedilir():
    """§12: celdirici evrende bilinen bir kelimeyse CEFR'i hedefi asamaz —
    yoksa soru hedef kelime yuzunden degil, CELDIRICI yuzunden zorlasir."""
    assert _broken(lambda a: a["questions"][0].update(
        options=["bank", "store", "cloud", "chair"])).reason == \
        "celdirici_cefr_hedefin_ustunde"


def test_evren_disi_celdirici_reddedilmez_uyarir():
    """Olculemeyen sey reddetmez (§12 son cumle)."""
    result = _broken(lambda a: a["questions"][0].update(
        options=["bank", "zzqx", "cloud", "chair"]))
    assert result.ok
    assert "celdirici_evren_disi_cefr_olculemedi" in result.reason


def test_celdiricinin_uymadigi_asla_reddetmez():
    """EN ONEMLI SOZ: anlamsal yakinlik olculemez (gomme katmani yok), bu
    yuzden bu kontrol RED DEGIL UYARIDIR ve her pakette gorunur."""
    # A1 secilmez: orada celdiricilerin kendisi (A2) ZATEN olculebilir
    # bicimde seviyeyi asar ve baska bir kapi reddeder.
    for cefr_level in ("A2", "B1", "B2", None):
        result = run(cloze_answer(), _unit(cefr=cefr_level))
        assert "celdiricinin_uymadigi_dogrulanamadi" in (result.reason or "")


# --- Seviye kapilari -------------------------------------------------------

def test_cumle_uzunlugu_bant_disindaysa_reddedilir():
    """"kolay" bandinin ust siniri asilirsa zorluk etiketi yalan olur."""
    assert _broken(lambda a: a["questions"][0].update(
        sentence="I keep all of my money and all of my papers in a bank near "
                 "the old station.")).reason == \
        "cumle_uzunlugu_zorluk_bandi_disinda"


def test_cumle_uzunlugu_bandin_bir_miktar_disindaysa_reddedilmez():
    """`WORD_COUNT_TOLERANCE` YALNIZCA QA'da genisler: model dar bandi
    duyar, olcen taraf payi verir. 13 kelimelik bir "zor" cumlesi (band
    15-25) odenmis haliyle cope ATILMAZ."""
    result = _broken(lambda a: a["questions"][2].update(
        sentence="After the meeting he walked to the bank to ask about the "
                 "rules."))
    assert result.ok


def test_seviye_ustu_kelime_reddedilir():
    """`loan` B2, anlam A2 -> cumle anlamin seviyesinin ustunde (iki band)."""
    assert _broken(lambda a: a["questions"][0].update(
        sentence="I keep my loan in a bank.")).reason == \
        "cumlede_anlamin_seviyesinin_ustunde_kelime"


def test_cefri_bilinmeyen_kelime_reddedilmez_uyarir():
    """Kabul olcutu (§10): 1000 kelimenin 160'inda CEFR YOK. Bilinmeyen
    seviye bir red gerekcesi DEGILDIR."""
    answer = copy.deepcopy(cloze_answer())
    # Seviye bilinseydi bu cumle `loan` yuzunden reddedilirdi.
    answer["questions"][0]["sentence"] = "I keep my loan in a bank."
    result = run(answer, _unit(cefr=None))
    assert result.ok
    assert "anlamin_cefri_bilinmiyor_kelime_dagarcigi_olculmedi" in result.reason


# --- Seviye sozlugu --------------------------------------------------------

def test_cekimli_bicim_kokunun_seviyesinden_okunur():
    """Sozlukte cekimli bicimler AYRI VE DAHA YUKSEK satirlar olabiliyor:
    `removed` C1 iken `remove` B1. Cekim cozulmezse dogru bir celdirici
    yalnizca gecmis zamanda yazildigi icin "seviyenin ustunde" sayilir —
    2026-09-07 kosusunda `add` fiili tam bunun yuzunden reddedildi."""
    seed_build_cefr((("remove", "verb", "B1"), ("removed", "verb", "C1"),
                     ("buy", "verb", "A1")))
    levels = cefr.load(dict_stages.lexicon_db_path(TAG))
    assert levels.get("removed", "verb") == "B1"   # yuzey C1, kok B1 -> kok
    assert levels.get("bought", "verb") == "A1"    # yuzey sozlukte HIC yok


def test_cekim_cozulur_turetme_cozulmez():
    """`wn.morphy` yalnizca CEKIM cozer. `healthy` ile `health` AYRI
    kelimelerdir ve seviyeleri de ayridir — biri digerini kurtarmamali."""
    seed_build_cefr((("health", "noun", "A2"), ("healthy", "adj", "B2")))
    levels = cefr.load(dict_stages.lexicon_db_path(TAG))
    assert levels.get("healthy", "adj") == "B2"


def test_sozlukte_olmayan_cekimli_bicim_hala_bilinmiyor_kalir():
    """Kok de sozlukte yoksa cevap yine `None`dir: cekim cozumu bir OLCUM
    genisletmesidir, uydurma degil."""
    seed_build_cefr((("bank", "noun", "A2"),))
    levels = cefr.load(dict_stages.lexicon_db_path(TAG))
    assert levels.get("sprinted", "verb") is None


def test_kelimenin_en_dusuk_seviyesi_kazanir():
    """POS bilinmiyorsa kelimeyi ogrencinin ILK gordugu seviye gecerlidir.
    `take` fiil olarak A1, isim olarak B1'dir -> A1.

    Regresyon: siralama `rank(...) or 99` ile yazilirsa A1'in sirasi 0 oldugu
    icin yanlis tarafa duser ve A1 her karsilastirmayi KAYBEDER. 2026-09-07
    kosusunda sozlugun 246 kelimesi bu yuzden hatali seviyedeydi."""
    seed_build_cefr((("take", "noun", "B1"), ("take", "verb", "A1"),
                     ("give", "verb", "A1"), ("give", "noun", "B1")))
    levels = cefr.load(dict_stages.lexicon_db_path(TAG))
    assert levels.get("take") == "A1"       # sira: once B1 satiri
    assert levels.get("give") == "A1"       # sira: once A1 satiri
    assert levels.get("take", "noun") == "B1"


def test_pos_sozlukte_yoksa_en_dusuk_seviyeye_dusulur():
    """Olculebilir bilgiyi POS eslesmedi diye cope atmayiz."""
    seed_build_cefr((("take", "verb", "A1"),))
    levels = cefr.load(dict_stages.lexicon_db_path(TAG))
    assert levels.get("take", "adv") == "A1"


# --- Tekduzelik ------------------------------------------------------------

def test_ayni_acilis_kalibi_reddedilir():
    """Kabul olcutu: bir anlamin uc cumlesi ayni acilis kalibiyla baslayamaz."""
    result = run(cloze_answer(sentences=[
        "I keep my money in a bank.",
        "I keep my cash inside the bank every single week.",
        "I keep my savings in the bank because the office near the park is "
        "shut today and tomorrow.",
    ]), _unit())
    assert result.reason == "uc_cumle_ayni_acilis_kalibi"


def test_tekduzelik_sayimi_qa_ile_ayni_tanimi_kullanir():
    """Panelin saydigi sey ile QA'nin reddettigi sey AYNI olmali."""
    assert opening_ngram("I keep my money in a bank.") == "i keep my"
    assert opening_ngram("I keep my cash inside the bank.") == "i keep my"


# --- Sahne kisiti ----------------------------------------------------------

def test_sahne_kisiti_deterministiktir():
    """Kabul olcutu: ayni birim iki kez planlandiginda AYNI kisit uretilir —
    saatten/rastgeleden/kosu kimliginden turemez."""
    assert scene.scenes_for("en:bank:noun") == scene.scenes_for("en:bank:noun")
    assert scene.scenes_for("en:bank:noun") != scene.scenes_for("en:run:verb")


def test_bir_anlamin_uc_sahnesi_farklidir():
    """Uc soruya ayni sahne verilseydi tekduzelik kapisi is bulurdu."""
    scenes = scene.scenes_for("en:bank:noun")
    assert len(set(scenes)) == 3


def test_sahne_prompta_ONERI_olarak_girer():
    """Sahne ZORUNLU yazilirsa iki istek ayni anda tutulamaz hale gelir
    (bu sahne + bu seviye), ve model sahneyi secip hedef kelimeyi ilgisiz
    bir cumleye sikistirir. 2026-09-07 kosusunda basarisiz 16 birimin 9'u
    buydu. Tutulamayan istek modele SOYLENMEZ (§6.7)."""
    from polyvo.modules.cloze import prompt

    text = prompt.build(_unit())
    scenes = scene.scenes_for("en:bank:noun")
    assert f"suggested setting: {scenes[0]}." in text
    assert "HINT for variety, not a requirement" in text
    assert "IGNORE the setting" in text


def test_prompt_celdiriciyi_sahneden_degil_hedeften_istemeyi_soyler():
    """Olculen kusur: bankacilik sahnesi A1 bir anlama "salary"/"debt"/
    "insurance" celdiricisi urettirdi ve CEFR kapisi HAKLI OLARAK reddetti.
    Kapi dogruydu, istek yanlisti."""
    from polyvo.modules.cloze import prompt

    text = prompt.build(_unit())
    assert "for the TARGET WORD, never for the setting" in text


def test_prompt_surumu_sahne_karari_ile_artti():
    """Surum artmasaydi onbellek ESKI prompt'un cevabini dondururdu ve
    degisiklik hicbir zaman olculemezdi."""
    from polyvo.modules.cloze.job import ClozeJob

    assert ClozeJob.prompt_version == "v2"


# --- Gosterim --------------------------------------------------------------

def test_bosluk_gosterimde_uretilir_depoda_tam_cumle_durur():
    """Ceviri 'boslugu doldurulmus tam cumlenin' cevirisidir (§14); bu yuzden
    depoda tam cumle durur, bosluk yalnizca gosterimde olusur."""
    assert render.blanked("I keep my money in a bank.", "bank") == \
        "I keep my money in a ____."
