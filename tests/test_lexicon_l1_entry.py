"""
`lexicon_card/translate` (tek paket: karsilik + ceviri) testleri — HICBIR AG
CAGRISI YOK: sahte saglayici gercek motoru, gercek QA'yi ve gercek depoyu
kullanir.

Eski `test_lexicon_gloss.py` + `test_lexicon_translate.py` burada birlesti
(Is 3b); ikisinin de sozleri korunur. Olculen sey: kartsiz/onaysiz anlam
birime girmez, kart bir daha ODENMEZ, tek birim = TEK cagri ve bes tablo,
paket HEPSI-YA-HIC, onayli/insan parca ezilmez, bir dil digerine dokunmaz,
eski iki QA'nin her red/uyari sebebi ayni sebeple cikar.
"""

from __future__ import annotations

import json

import pytest

from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.jobs.store.policy import TIER_HUMAN
from polyvo.core.llm.base import LLMResult
from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema
from polyvo.modules.lexicon_card.store import LexiconCardStore
from polyvo.modules.lexicon_card.translate import prompt as prompt_mod
from polyvo.modules.lexicon_card.translate import qa as qa_mod, units
from polyvo.modules.lexicon_card.translate.job import LexiconL1EntryJob
from polyvo.modules.lexicon_card.translate.store import LexiconL1EntryStore

TAG, L2, L1 = "test", "en", "tr"
QWEN = "cloudflare:@cf/qwen/qwen3-30b-a3b-fp8"

CARD_ANSWER = {
    "gloss_en": "to move quickly on foot",
    "register": "neutral",
    "usage_note": "",
    "examples": ["I run every morning before work.",
                 "They ran across the empty field."],
}

TR_ANSWER = {
    "gloss_l1": "koşmak",
    "gloss_note": "",
    "definition": "ayakla hizlica hareket etmek",
    "usage_note": "",
    "examples": ["Her sabah işten önce koşarım.", "Boş tarlada koştular."],
}

ES_ANSWER = {
    "gloss_l1": "correr",
    "gloss_note": "",
    "definition": "moverse rápidamente a pie",
    "usage_note": "",
    "examples": ["Corro todas las mañanas antes del trabajo.",
                 "Corrieron por el campo vacío."],
}

#: `run` (verb) icin her dilde QA'dan gecen karsilik — ceviri kapisini
#: olcen testlerde karsilik parcasi red sebebi URETMESIN diye.
GLOSS_BY_L1 = {"tr": "koşmak", "es": "correr", "pt-BR": "correr", "de": "laufen"}

TABLES = ("sense_gloss_l1", "sense_gloss_l1_note", "sense_gloss_l1_state",
          "sense_translation", "sense_translation_examples")


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


class FakeProvider:
    """`complete_json` sozlesmesini taklit eden, agi olmayan saglayici."""

    def __init__(self, answer=None, label=QWEN):
        self.label = label
        self.answer = answer if answer is not None else TR_ANSWER
        self.calls: list[str] = []

    def preflight(self):
        """Sahte on-kontrol — her zaman gecer."""
        return None

    def peek_cached(self, prompt, cache_conn):
        """Onbellekteki cevabi cagri yapmadan doner; yoksa None."""
        hit = get_cached(cache_conn, hash_prompt(self.label, prompt))
        if hit is None:
            return None
        return LLMResult(json.loads(hit), True, hit)

    def complete_json(self, prompt, cache_conn, *, max_tokens, temperature,
                      pace_delay=0.0, bypass_cache=False):
        """Onbellek-once davranisi dahil sahte bir cagri."""
        h = hash_prompt(self.label, prompt)
        hit = None if bypass_cache else get_cached(cache_conn, h)
        if hit is not None:
            return LLMResult(json.loads(hit), True, hit)
        self.calls.append(prompt)
        raw = json.dumps(self.answer, ensure_ascii=False)
        store_cached(cache_conn, h, self.label, prompt, raw)
        return LLMResult(json.loads(raw), False, raw)


def _seed_universe(rows=(("run", "verb", "A1", 5),)):
    """Test evrenini `workspace/<tag>/<l2>/universe.sqlite`'a yazar."""
    conn = curriculum_schema.open_universe_db(TAG, L2)
    with conn:
        conn.executemany(
            "INSERT INTO universe_items (item_id, sense_id, l2, headword, pos,"
            " cefr, freq_rank, stable_key) VALUES (?,?,?,?,?,?,?,?)",
            [(i, 1000 + i, L2, head, pos, cefr, rank, f"{L2}:{head}:{pos}")
             for i, (head, pos, cefr, rank) in enumerate(rows, start=1)])
    conn.close()


def _seed_card(headword="run", pos="verb", answer=None):
    """`sense_cards`a ONAYLI bir kart yazar. Kart HICBIR dilde
    `sense_gloss_l1`e yazmaz — bu yuzden `l1` parametresi yok."""
    from polyvo.modules.lexicon_card import units as card_units

    unit = next(u for u in card_units.load_units(TAG, L2)
               if u.data["headword"] == headword and u.data["pos"] == pos)
    store = LexiconCardStore()
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload=answer or CARD_ANSWER, tier=3,
        model_label=QWEN), None)
    store.commit()
    store.close()


def _seed_part(l1, payload, *, tier=3, model_label=QWEN):
    """Depoya TEK bir parca yazar (yalnizca karsilik ya da yalnizca ceviri)
    — eski `gloss`/`translate` kosularindan kalan satirlarin taklidi."""
    from polyvo.core.jobs import keys as keys_mod

    unit = units.load_units(TAG, L2, l1)[0]
    store = LexiconL1EntryStore()
    store.save(JobContext(tag=TAG, l2=L2, l1=l1, variant=l1),
               WriteRequest(unit=keys_mod.with_variant(unit, l1),
                            payload=payload, tier=tier,
                            model_label=model_label), None)
    store.commit()
    store.close()


def _rows(l1):
    """Bes tablonun o dile ait butun satirlari — dokunulmadigini olcmek icin."""
    conn = schema.open_lexicon_db()
    try:
        return {t: [tuple(r) for r in conn.execute(
                    f"SELECT * FROM {t} WHERE l1 = ? ORDER BY 1, 2", (l1,))]
                for t in TABLES}
    finally:
        conn.close()


def _run(provider, l1=L1, **kwargs):
    """Motoru sahte saglayiciyla ucdan uca kosturur."""
    store = LexiconL1EntryStore()
    try:
        return engine_run.run(LexiconL1EntryJob(),
                              JobContext(tag=TAG, l2=L2, l1=l1, variant=l1),
                              provider=provider, store=store, assume_yes=True,
                              **kwargs)
    finally:
        store.close()


# --- Birim yukleme ---------------------------------------------------------

def test_kartsiz_anlam_birim_listesine_girmez():
    _seed_universe((("run", "verb", "A1", 5), ("apple", "noun", "A1", 9)))
    _seed_card("run", "verb")
    loaded = units.load_units(TAG, L2, L1)
    assert [u.key for u in loaded] == ["en:run:verb"]


def test_onaysiz_kart_birim_listesine_girmez():
    from polyvo.modules.lexicon_card import units as card_units

    _seed_universe()
    unit = card_units.load_units(TAG, L2)[0]
    store = LexiconCardStore()
    # Reddedilmis bir kart taklit edilir: icerik BOS, status='rejected'.
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload={}, status="rejected", tier=3,
        reject_reason="test_red", model_label="x"), None)
    store.commit()
    store.close()

    assert units.load_units(TAG, L2, L1) == []


def test_onayli_karsilik_birime_sabit_terim_olarak_girer():
    """Depodaki karsilik YALNIZCA kendi dilinin birimine girer."""
    _seed_universe()
    _seed_card("run", "verb")
    _seed_part("es", {"gloss_l1": "correr"})
    assert units.load_units(TAG, L2, "es")[0].data["card"]["fixed_gloss"] == "correr"
    assert units.load_units(TAG, L2, "tr")[0].data["card"]["fixed_gloss"] == ""


# --- Prompt ---------------------------------------------------------------

def test_prompt_anlamin_tamamini_tek_istekte_baglam_verir():
    """Model kelimeyi degil o ANLAMI isler: kartin gloss_en'i ve iki ornegi
    BAGLAM olarak AYNI istekte; bes alanin hepsi TEK JSON'da istenir."""
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2, L1)[0]
    text = prompt_mod.build(unit, "tr")
    assert CARD_ANSWER["gloss_en"] in text
    assert CARD_ANSWER["examples"][0] in text
    assert CARD_ANSWER["examples"][1] in text
    for field in ("gloss_l1", "gloss_note", "definition", "usage_note", "examples"):
        assert f'"{field}"' in text


def test_prompt_onayli_karsiligi_sabit_terim_olarak_dayatir():
    _seed_universe()
    _seed_card("run", "verb")
    _seed_part("tr", {"gloss_l1": "koşmak"})
    unit = units.load_units(TAG, L2, "tr")[0]
    text = prompt_mod.build(unit, "tr")
    assert 'use EXACTLY this Turkish equivalent for the word: "koşmak"' in text


# --- QA: karsilik parcasi (eski gloss QA'si) -------------------------------

def _unit(headword="run", pos="verb", l1=L1):
    """QA icin tek birim (kartiyla birlikte)."""
    _seed_universe(((headword, pos, "A1", 5),))
    _seed_card(headword, pos)
    return units.load_units(TAG, L2, l1)[0]


@pytest.mark.parametrize("bozuk,sebep", [
    (None, "cevap_json_degil"),
    ({"gloss_l1": ""}, "gloss_l1_bos"),
    ({"gloss_l1": "x" * 90}, "gloss_l1_karsilik_degil_cumle"),
    ({"gloss_l1": CARD_ANSWER["gloss_en"]}, "gloss_l1_kart_kopyasi"),
    ({"gloss_l1": "corre"}, "verb_missing_infinitive"),
    # Uzun ve Ingilizce: dil kapisi BURADA reddeder (ayirt etme gucu var).
    ({"gloss_l1": "to move quickly"}, "l1_ceviri_yapilmamis"),
])
def test_qa_bozuk_cevabi_sebebiyle_reddeder(bozuk, sebep):
    unit = _unit(l1="es")
    parsed = None if bozuk is None else {**ES_ANSWER, **bozuk}
    result = qa_mod.run(parsed, unit, "es")
    assert not result.ok and result.reason == sebep


@pytest.mark.parametrize("headword,pos,cevap", [
    ("non", "adv", "no"),        # es pilotunda reddedilmisti — DOGRU cevap
    ("to", "prep", "a"),         # es pilotunda reddedilmisti — DOGRU cevap
])
def test_kisa_islev_sozcugu_dil_kapisinda_reddedilmez(headword, pos, cevap):
    """OLCULDU (es pilotu, 2026-09-06): bu birimler dogru Ispanyolca cevap
    verdigi halde `l1_ceviri_yapilmamis` ile reddedildi. `no`/`a` Ispanyolca'da
    da gecen isaretcilerdir (`ENGLISH_AMBIGUOUS`) — supheli bir sey yok."""
    unit = _unit(headword, pos, l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": cevap}, unit, "es")
    assert result.ok
    assert result.payload["gloss_l1"] == cevap
    assert "l1_ceviri_supheli_kisa_karsilik" not in (result.reason or "")


def test_kisa_ama_AYIRT_EDICI_ingilizce_cevap_uyari_birakir():
    """`the` Ispanyolca'da gecmez, gercek bir Ingilizce kanitidir — ama cevap
    3 kelimeden kisa oldugu icin REDDETMEZ, iz birakir (§6.7)."""
    unit = _unit("run", "noun", l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": "the act"}, unit, "es")
    assert result.ok
    assert "l1_ceviri_supheli_kisa_karsilik" in result.reason


def test_uzun_ingilizce_cevap_hala_reddedilir():
    """Kapi kaldirilmadi, KOSULLANDI: cevap uzadikca sinyal anlam kazanir."""
    unit = _unit("run", "noun", l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": "the act of moving"}, unit, "es")
    assert not result.ok and result.reason == "l1_ceviri_yapilmamis"


def test_es_kokenli_karsilik_kelimenin_kendisi_olabilir():
    """`hotel` -> `hotel` DOGRU Ispanyolcadir -> uyari, red degil."""
    unit = _unit("hotel", "noun", l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": "hotel"}, unit, "es")
    assert result.ok
    assert "l1_karsilik_kelimenin_kendisiyle_ayni" in result.reason


def test_kartin_ingilizce_tanimini_kopyalamak_hala_reddedilir():
    """Kelimenin kendisi uyari, ama kartin TANIMINI geri dondurmek red."""
    unit = _unit("run", "verb", l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": CARD_ANSWER["gloss_en"]}, unit, "es")
    assert not result.ok and result.reason == "gloss_l1_kart_kopyasi"


@pytest.mark.parametrize("headword,cevap", [
    ("box", "kutu"), ("cat", "kedi"), ("warranty", "garanti"),
    ("bad", "kötü"), ("breakfast", "kahvaltı"),
])
def test_tr_siradan_isim_looks_conjugated_ile_reddedilmez(headword, cevap):
    """OLCULDU (kart gunlugu): `looks_conjugated` neredeyse hep YANLIS
    ALARMDI — bu isimlerin hepsi `-di/-ti/-tu/-tu` ile biter -> uyari."""
    unit = _unit(headword, "noun")
    result = qa_mod.run({**TR_ANSWER, "gloss_l1": cevap}, unit, "tr")
    assert result.ok
    assert "looks_conjugated" in result.reason


def test_tr_fiil_mastar_kapisi_HALA_reddeder():
    """Yumusatma fiil kapisini kapsamaz: o kapi olculdu ve dogru calisiyor."""
    unit = _unit("run", "verb")
    result = qa_mod.run({**TR_ANSWER, "gloss_l1": "koşuyor"}, unit, "tr")
    assert not result.ok and result.reason == "verb_missing_infinitive"


def test_tr_bozuk_mastar_kapisi_burada_da_calisir():
    """`tr.py`nin mastar kapisi (`-mek/-mak`) bu iste de gecerli — ikinci
    bir kural kumesi yazilmadi, `l1_form.py` tek tanimi paylasiyor."""
    unit = _unit("run", "verb")
    result = qa_mod.run({**TR_ANSWER, "gloss_l1": "koşuyor"}, unit, "tr")
    assert not result.ok and result.reason == "verb_missing_infinitive"


# --- QA: ceviri parcasi (eski translate QA'si), HEPSI-YA-HIC --------------

def test_tanim_bossa_reddedilir():
    unit = _unit()
    result = qa_mod.run({**TR_ANSWER, "definition": ""}, unit, "tr")
    assert not result.ok and result.reason == "tanim_bos"


def test_ornek_sayisi_kaynaktan_farkliysa_reddedilir():
    unit = _unit()
    result = qa_mod.run({**TR_ANSWER, "examples": ["tek cumle"]}, unit, "tr")
    assert not result.ok and result.reason == "ornek_sayisi_uyusmuyor"


def test_tanim_ceviri_yerine_ingilizce_kalirsa_reddedilir():
    unit = _unit()
    result = qa_mod.run(
        {**TR_ANSWER, "definition": CARD_ANSWER["gloss_en"]}, unit, "tr")
    assert not result.ok and result.reason == "ceviri_yapilmamis"


def test_tanim_hala_ingilizceyse_dil_kapisi_reddeder():
    unit = _unit()
    result = qa_mod.run(
        {**TR_ANSWER, "definition": "to move very fast on foot"}, unit, "tr")
    assert not result.ok and result.reason == "l1_ceviri_yapilmamis"


def test_kaynak_notu_var_ceviri_notu_boslarsa_reddedilir():
    _seed_universe()
    _seed_card("run", "verb")
    from polyvo.modules.lexicon_card.note.store import LexiconNoteStore
    from polyvo.modules.lexicon_card.note import units as note_units

    unit0 = note_units.load_units(TAG, L2)[0]
    note_store = LexiconNoteStore()
    note_store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit0, payload={"reason": "idiom", "note": "Managing a business."},
        model_label="x"), None)
    note_store.commit()
    note_store.close()

    unit = units.load_units(TAG, L2, L1)[0]
    assert unit.data["card"]["usage_note"] == "Managing a business."
    result = qa_mod.run({**TR_ANSWER, "usage_note": ""}, unit, "tr")
    assert not result.ok and result.reason == "ceviri_notu_eksik"


def test_paket_gecerliyse_hepsi_birden_onaylanir():
    unit = _unit()
    result = qa_mod.run(TR_ANSWER, unit, "tr")
    assert result.ok
    assert result.payload["gloss_l1"] == TR_ANSWER["gloss_l1"]
    assert result.payload["definition"] == TR_ANSWER["definition"]
    assert result.payload["examples"] == TR_ANSWER["examples"]


def test_cevap_json_degilse_reddedilir():
    unit = _unit()
    result = qa_mod.run(None, unit, "tr")
    assert not result.ok and result.reason == "cevap_json_degil"


# Yanlis red regresyonu: GERCEK kosunun reddettigi DOGRU ceviriler.
# OLCULDU (v7 deposu, 2026-09-07): `de` 6, `pt-BR` 5, `es` 2 birim
# `l1_ceviri_yapilmamis` ile reddedildi; ON UCUNUN DE cevirisi DOGRUYDU.
# Asagidaki metinler o kosunun HAM cevaplaridir, elle yazilmis ornek DEGIL.

GERCEK_YANLIS_REDLER = [
    ("de", "in der Lage sein, etwas zu tun",
     ["Sie ist in der Lage, das Problem schnell zu lösen.",
      "Er ist in der Lage, drei Sprachen zu sprechen."]),
    ("de", "Eine Person, die die Dienste eines Profis in Anspruch nimmt.",
     ["Der Kunde traf mit dem Anwalt zusammen.",
      "Der Kunde unterschrieb den Vertrag."]),
    ("de", "Ein Titel, der verwendet wird, um einen Mann anzusprechen.",
     ["Herr, könnten Sie mir helfen?", "Herr Johnson wartet in der Lobby."]),
    ("es", "aproximadamente; concerniente o relativo a algo",
     ["Tengo aproximadamente diez minutos restantes.",
      "Ella habló de sus viajes."]),
    ("es", "Se usa para indicar que algo no está sucediendo o no es cierto",
     ["No estoy cansado, soy no", "No vino, es no"]),
    ("pt-BR", "Itens que são vendidos ou trocados.",
     ["A loja vende diferentes tipos de mercadorias.",
      "Eles transportaram as mercadorias por caminhão."]),
    ("pt-BR", "Relativo a algo ou alguém.",
     ["Ela falou sobre suas viagens.", "Eu li sobre o evento no jornal."]),
    ("pt-BR", "Tornar algo disponível ao público por meio de impressão ou distribuição.",
     ["A autora publicou seu primeiro romance no ano passado.",
      "A revista publicou um artigo sobre mudanças climáticas."]),
]


@pytest.mark.parametrize("l1,definition,examples", GERCEK_YANLIS_REDLER)
def test_gercek_kosudaki_dogru_ceviri_reddedilmez(l1, definition, examples):
    """Bu paketlerin HEPSI dogru cevirilerdir ve kapidan GECMELIDIR. Duserse
    dil kapisi yeniden yanlis alarm uretiyor demektir."""
    unit = _unit(l1=l1)
    result = qa_mod.run(
        {"gloss_l1": GLOSS_BY_L1[l1], "definition": definition,
         "usage_note": "", "examples": examples}, unit, l1)
    assert result.ok, result.reason
    assert result.payload["definition"] == definition


@pytest.mark.parametrize("l1", ["tr", "es", "pt-BR", "de"])
def test_kaynak_ingilizce_aynen_dondurulurse_hala_reddedilir(l1):
    """"Model cevirmedi" karari GARANTI EDILEBILIR katmanda (kaynak metinle
    karsilastirma) — dort dilde de calisir."""
    unit = _unit(l1=l1)
    result = qa_mod.run(CARD_ANSWER | {"gloss_l1": GLOSS_BY_L1[l1],
                                       "definition": CARD_ANSWER["gloss_en"],
                                       "usage_note": ""}, unit, l1)
    assert not result.ok and result.reason == "ceviri_yapilmamis"


@pytest.mark.parametrize("l1", ["tr", "es", "pt-BR", "de"])
def test_ornek_cumle_cevrilmemisse_reddedilir(l1):
    """Tanim cevrilmis ama ORNEK Ingilizce kalmissa da paket reddedilir."""
    unit = _unit(l1=l1)
    result = qa_mod.run(
        {"gloss_l1": GLOSS_BY_L1[l1], "definition": "cevrilmis bir tanımçğş",
         "usage_note": "",
         "examples": [CARD_ANSWER["examples"][0], "ikinci çeviri cümlesi"]},
        unit, l1)
    assert not result.ok and result.reason == "ceviri_yapilmamis"


# --- QA: terim tutarliligi (YALNIZCA uyari) --------------------------------

def test_karsilik_orneklerde_gecmiyorsa_uyari_red_degil():
    unit = _unit()
    result = qa_mod.run({**TR_ANSWER, "gloss_l1": "seğirtmek"}, unit, "tr")
    assert result.ok
    assert "gloss_terimi_orneklerde_yok" in result.reason


def test_karsilik_cekimli_bicimde_gecerse_uyari_yok():
    """"koşmak" -> "koşarım"/"koştular": cekim ayni terimdir."""
    unit = _unit()
    result = qa_mod.run(TR_ANSWER, unit, "tr")
    assert result.ok
    assert "gloss_terimi_orneklerde_yok" not in (result.reason or "")


def test_terim_kontrolu_olculmemis_dilde_calismaz():
    """`TERM_MATCH_SUPPORTED` acik olmayan dilde (es) kontrol susar."""
    unit = _unit(l1="es")
    result = qa_mod.run({**ES_ANSWER, "gloss_l1": "trotar"}, unit, "es")
    assert result.ok
    assert "gloss_terimi_orneklerde_yok" not in (result.reason or "")


# --- Uctan uca kosu ------------------------------------------------------

def test_dry_run_tek_kurus_harcamaz_tek_satir_yazmaz():
    _seed_universe((("run", "verb", "A1", 5), ("go", "verb", "A1", 6)))
    _seed_card("run", "verb")
    _seed_card("go", "verb", answer={**CARD_ANSWER, "gloss_en": "to move",
                                     "examples": ["I go home.", "They go far."]})
    provider = FakeProvider()
    result = _run(provider, dry_run=True)
    assert result.plan.process_total == 2
    assert provider.calls == []
    assert result.new_calls == 0
    assert all(rows == [] for rows in _rows(L1).values())


def test_tek_birim_tek_cagri_bes_tablo_dolar():
    """Is 3b'nin varlik sebebi: karsilik + not + ceviri + ornekler TEK
    cagrida uretilir ve bes tablonun hepsi dolar."""
    _seed_universe()
    _seed_card("run", "verb")
    provider = FakeProvider(answer={**TR_ANSWER, "gloss_note": "kisa not"})
    result = _run(provider)
    assert len(provider.calls) == 1
    assert result.new_calls == 1 and result.approved == 1
    assert all(len(rows) >= 1 for rows in _rows(L1).values()), _rows(L1)


def test_ceviri_yazilir_kart_dokunulmadan_kalir():
    _seed_universe()
    _seed_card("run", "verb")
    result = _run(FakeProvider())
    assert result.approved == 1 and result.new_calls == 1

    conn = schema.open_lexicon_db()
    gloss = conn.execute("SELECT gloss FROM sense_gloss_l1 WHERE l1='tr'").fetchone()
    row = conn.execute(
        "SELECT definition, status FROM sense_translation WHERE l1='tr'").fetchone()
    examples = [r[0] for r in conn.execute(
        "SELECT text FROM sense_translation_examples WHERE l1='tr' ORDER BY seq")]
    card = conn.execute("SELECT gloss_en FROM sense_cards").fetchone()
    conn.close()
    assert gloss[0] == TR_ANSWER["gloss_l1"]
    assert row["definition"] == TR_ANSWER["definition"]
    assert row["status"] == "approved"
    assert examples == TR_ANSWER["examples"]
    assert card["gloss_en"] == CARD_ANSWER["gloss_en"]     # kart hic dokunulmadi


def test_gloss_l1_artik_bu_isin_kapsaminda_sense_gloss_l1e_yazilir():
    """SOZU BILEREK TERSINE DONDU (Is 3b): eskiden `translate` kelime
    karsiligini uretmezdi. Artik karsilik ayni cagrinin parcasidir."""
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider())

    conn = schema.open_lexicon_db()
    count = conn.execute("SELECT COUNT(*) FROM sense_gloss_l1").fetchone()[0]
    conn.close()
    assert count == 1


def test_kosudan_sonra_kart_yeniden_tetiklenmez():
    """Paket kosusu kartin anahtarina DOKUNMAZ: `cards` bir daha odenmez."""
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer=ES_ANSWER), l1="es")

    from polyvo.modules.lexicon_card.job import LexiconCardJob
    store = LexiconCardStore()
    try:
        result = engine_run.run(
            LexiconCardJob(), JobContext(tag=TAG, l2=L2),
            provider=FakeProvider(answer=CARD_ANSWER), store=store,
            assume_yes=True, dry_run=True)
    finally:
        store.close()
    assert result.plan.paid_calls == 0


def test_ikinci_kosuda_hic_odenmis_cagri_yapilmaz():
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider())

    provider = FakeProvider()
    second = _run(provider)
    assert second.plan.paid_calls == 0
    assert second.new_calls == 0
    assert provider.calls == []


def test_karsilik_reddedilirse_ceviri_de_yazilmaz_durum_iz_birakir():
    """Hepsi ya da hic: karsilik parcasi reddedilince DOGRU ceviri de
    yazilmaz; iki parcanin durum satiri 'rejected' der."""
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer={**ES_ANSWER, "gloss_l1": "corre"}), l1="es")

    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT COUNT(*) FROM sense_gloss_l1"
                        " WHERE l1='es'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sense_translation_examples"
                        " WHERE l1='es'").fetchone()[0] == 0
    state = conn.execute(
        "SELECT status, reject_reason FROM sense_gloss_l1_state"
        " WHERE l1='es'").fetchone()
    entry = conn.execute(
        "SELECT definition, status, reject_reason FROM sense_translation"
        " WHERE l1='es'").fetchone()
    conn.close()
    assert state["status"] == "rejected"
    assert state["reject_reason"] == "verb_missing_infinitive"
    assert entry["definition"] is None and entry["status"] == "rejected"
    assert entry["reject_reason"] == "verb_missing_infinitive"


def test_ceviri_reddedilirse_karsilik_da_yazilmaz_durum_iz_birakir():
    """Tersi de ayni: ceviri parcasi reddedilince DOGRU karsilik yazilmaz."""
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer={**TR_ANSWER, "definition": ""}))

    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT COUNT(*) FROM sense_gloss_l1").fetchone()[0] == 0
    row = conn.execute(
        "SELECT definition, status, reject_reason FROM sense_translation"
        " WHERE l1='tr'").fetchone()
    state = conn.execute(
        "SELECT status, reject_reason FROM sense_gloss_l1_state"
        " WHERE l1='tr'").fetchone()
    conn.close()
    assert row["definition"] is None
    assert row["status"] == "rejected"
    assert row["reject_reason"] == "tanim_bos"
    assert (state["status"], state["reject_reason"]) == ("rejected", "tanim_bos")


def test_redo_bad_daha_iyi_model_reddedilen_satiri_bulur():
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer={**ES_ANSWER, "gloss_l1": "corre"}), l1="es")

    better = FakeProvider(answer=ES_ANSWER,
                          label="gemini:gemini-2.5-pro")   # rank 10 < 40
    result = _run(better, l1="es", redo="bad")
    assert result.plan.paid_calls == 1
    assert result.approved == 1

    conn = schema.open_lexicon_db()
    gloss = conn.execute(
        "SELECT gloss FROM sense_gloss_l1 WHERE l1='es'").fetchone()
    conn.close()
    assert gloss[0] == "correr"


def test_redo_none_reddedilen_satiri_bulmaz():
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer={**ES_ANSWER, "gloss_l1": "corre"}), l1="es")

    provider = FakeProvider(answer=ES_ANSWER)
    result = _run(provider, l1="es")              # varsayilan redo=none
    assert result.plan.paid_calls == 0
    assert provider.calls == []


def test_bir_dilin_kosusu_diger_dile_dokunmaz():
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider())                          # tr
    before = _rows("tr")
    assert before["sense_translation"]

    _run(FakeProvider(answer=ES_ANSWER), l1="es")
    assert _rows("tr") == before                  # tr bit bit ayni
    assert len(_rows("es")["sense_translation"]) == 1

    # `es` yazildiktan sonra `de` hala bos, ayri kosuda uretilebilir.
    de_result = _run(FakeProvider(), l1="de", dry_run=True)
    assert de_result.plan.process_total == 1
    assert de_result.plan.paid_calls == 1


def test_onayli_karsilik_varken_eksik_ceviri_icin_cagrilir_karsilik_degismez():
    """Karsilik onayli, ceviri eksik: birim cagrilir; model FARKLI bir
    karsilik dondurse bile onayli satirin uzerine yazilmaz (yazma kapisi)."""
    _seed_universe()
    _seed_card("run", "verb")
    _seed_part("es", {"gloss_l1": "correr"})
    gloss_before = _rows("es")["sense_gloss_l1"]

    provider = FakeProvider(answer={**ES_ANSWER, "gloss_l1": "trotar"})
    result = _run(provider, l1="es")
    assert len(provider.calls) == 1 and result.approved == 1
    assert '"correr"' in provider.calls[0]        # sabit terim promptta
    after = _rows("es")
    assert after["sense_gloss_l1"] == gloss_before
    assert len(after["sense_translation"]) == 1


def test_insan_karsiligi_varken_eksik_ceviri_icin_cagrilir_karsilik_degismez():
    """Sabit terim QA'DAN AYNEN gecer (karar: model yine dondurur, kapi
    degismez) — bu yuzden insan karsiligi da gecerli bir TR mastar olmali."""
    _seed_universe()
    _seed_card("run", "verb")
    _seed_part("tr", {"gloss_l1": "koşmak"}, tier=TIER_HUMAN, model_label=None)

    provider = FakeProvider(answer={**TR_ANSWER, "gloss_l1": "koşmak"})
    result = _run(provider)
    assert len(provider.calls) == 1
    assert result.approved == 1

    conn = schema.open_lexicon_db()
    gloss = conn.execute(
        "SELECT gloss, tier FROM sense_gloss_l1 WHERE l1='tr'").fetchone()
    entry = conn.execute(
        "SELECT status FROM sense_translation WHERE l1='tr'").fetchone()
    conn.close()
    assert tuple(gloss) == ("koşmak", TIER_HUMAN)
    assert entry["status"] == "approved"


def test_insan_satirina_model_dokunamaz():
    """Iki parca da insan: plan cagri istemez, satirlar oldugu gibi kalir."""
    _seed_universe()
    _seed_card("run", "verb")
    _seed_part("tr", {"gloss_l1": "insan karsiligi"},
               tier=TIER_HUMAN, model_label=None)
    _seed_part("tr", {"definition": "insan cevirisi", "usage_note": "",
                      "examples": ["a", "b"]},
               tier=TIER_HUMAN, model_label=None)

    provider = FakeProvider()
    result = _run(provider)
    assert provider.calls == []
    assert result.plan.paid_calls == 0

    conn = schema.open_lexicon_db()
    gloss = conn.execute("SELECT gloss FROM sense_gloss_l1 WHERE l1='tr'").fetchone()
    row = conn.execute(
        "SELECT definition FROM sense_translation WHERE l1='tr'").fetchone()
    conn.close()
    assert gloss[0] == "insan karsiligi"
    assert row["definition"] == "insan cevirisi"


def test_tr_de_ayni_yoldan_calisir():
    """DORT DIL DE TEK YOLDAN uretilir: `tr` icin ayri kod yolu/bayrak/
    istisna YOK — ayni job, ayni QA."""
    _seed_universe()
    _seed_card("run", "verb")                     # kartin hicbir L1 karsiligi YOK

    result = _run(FakeProvider(), l1="tr")
    assert result.approved == 1 and result.new_calls == 1

    conn = schema.open_lexicon_db()
    gloss = conn.execute(
        "SELECT gloss FROM sense_gloss_l1 WHERE l1='tr'").fetchone()
    conn.close()
    assert gloss[0] == "koşmak"

    second = _run(FakeProvider(), l1="tr")        # artimlilik burada da gecerli
    assert second.plan.paid_calls == 0


def test_besinci_dil_sema_degisikligi_olmadan_planlanir():
    """`l1` bir SUTUNDUR: uydurma bir kod (`fr`) icin DDL degismeden plan
    kurulabilir — Is 3 madde 10."""
    _seed_universe()
    _seed_card("run", "verb")
    result = _run(FakeProvider(), l1="fr", dry_run=True)
    assert result.plan.process_total == 1
    assert result.plan.paid_calls == 1


def test_gloss_komutu_kaldirildi_exit_2():
    """`lexicon-card gloss` artik yok: sessiz yok sayma degil, exit 2."""
    from polyvo.core.cli import main as cli_main

    with pytest.raises(SystemExit) as exc:
        cli_main.main(["lexicon-card", "gloss", "--l1", "tr"])
    assert exc.value.code == 2


# --- Kaynak denetimi: tek yazici -----------------------------------------

def test_sense_translationa_yazan_tek_dosya_translate_deposudur():
    """KAYNAK DENETIMI: `sense_translation`(+`_examples`)e yazan tek dosya
    `translate/store.py` olmali."""
    import os
    import re

    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "polyvo", "modules", "lexicon_card")
    pattern = re.compile(
        r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+sense_translation"
        r"|UPDATE\s+sense_translation"
        r"|DELETE\s+FROM\s+sense_translation",
        re.IGNORECASE)

    writers = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                if pattern.search(f.read()):
                    writers.append(os.path.relpath(path, root).replace("\\", "/"))

    assert sorted(writers) == ["translate/store.py"], (
        "`sense_translation`a yazan dosyalar: " + ", ".join(sorted(writers)))
