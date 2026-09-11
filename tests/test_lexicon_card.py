"""
`lexicon_card` testleri — HICBIR AG CAGRISI YOK: sahte saglayici gercek
motoru, gercek QA'yi ve gercek depoyu kullanir.

Olculen sey Adim 5'in kabul kriterleridir: kart butun parcalariyla yazilir,
IKINCI KOSUDA `paid_calls = 0` (artimlilik), QA kotu cevabi REDDEDER ve
reddedilen satir icerik yazmaz, insan satirina dokunulmaz.

Is 2b'den sonra buraya bir sey daha eklendi: kart DILE BAGLI DEGILDIR —
`sense_gloss_l1`e tek satir yazmaz ve `gloss_l1` yuzunden REDDETMEZ.
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
from polyvo.modules.lexicon_card import qa as qa_mod, schema, seed, units
from polyvo.modules.lexicon_card.job import LexiconCardJob
from polyvo.modules.lexicon_card.store import LexiconCardStore

TAG, L2, L1 = "test", "en", "tr"

GOOD_ANSWER = {
    "gloss_en": "to move quickly on foot",
    "register": "neutral",
    "usage_note": "",
    "examples": ["I run every morning before work.",
                 "They ran across the empty field."],
}


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


class FakeProvider:
    """`complete_json` sozlesmesini taklit eden, agi olmayan saglayici."""

    def __init__(self, answer=None, label="cloudflare:@cf/qwen/qwen3-30b-a3b-fp8"):
        self.label = label
        self.answer = answer if answer is not None else GOOD_ANSWER
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


def _run(provider, **kwargs):
    """Motoru sahte saglayiciyla ucdan uca kosturur."""
    store = LexiconCardStore()
    try:
        # `l1` BILEREK doldurulur: kart kosusu ctx.l1'i gorse bile
        # `sense_gloss_l1`e tek satir yazmamali (Is 2b).
        return engine_run.run(LexiconCardJob(), JobContext(tag=TAG, l2=L2, l1=L1),
                              provider=provider, store=store, assume_yes=True,
                              **kwargs)
    finally:
        store.close()


# --- Birim yukleme -------------------------------------------------------

def test_birimler_item_id_sirasinda_ve_stable_key_ile_gelir():
    _seed_universe((("run", "verb", "A1", 5), ("apple", "noun", "A1", 9)))
    loaded = units.load_units(TAG, L2)
    assert [u.key for u in loaded] == ["en:run:verb", "en:apple:noun"]
    assert loaded[0].data["sense_id"] == 1001


def test_tohum_dosyasi_yoksa_kosu_durmaz():
    assert seed.load_seeds("yok-boyle-bir-dosya.sqlite", ["run"]) == {}


# --- QA kapisi -----------------------------------------------------------

def _unit(headword="run", pos="verb"):
    """QA testleri icin tek bir birim."""
    _seed_universe(((headword, pos, "A1", 5),))
    return units.load_units(TAG, L2)[0]


@pytest.mark.parametrize("bozuk,sebep", [
    (None, "cevap_json_degil"),
    ({**GOOD_ANSWER, "gloss_en": ""}, "gloss_en_bos"),
    ({**GOOD_ANSWER, "gloss_en": "to run fast"}, "gloss_en_kelimenin_kendisini_iceriyor"),
    ({**GOOD_ANSWER, "examples": ["I run every day."]}, "ornek_sayisi_yetersiz"),
    ({**GOOD_ANSWER, "examples": ["I run.", "I run."]}, "ornek_cumle_cok_kisa"),
    ({**GOOD_ANSWER, "examples": ["I run every day.", "I  run every  day."]},
     "ornekler_ayni"),
])
def test_qa_bozuk_cevabi_sebebiyle_reddeder(bozuk, sebep):
    result = qa_mod.run(bozuk, _unit())
    assert not result.ok and result.reason == sebep


def test_gloss_l1i_olmayan_cevap_kabul_edilir():
    """IS 2B'NIN VARLIK SEBEBI. Modelin cevabinda `gloss_l1` HIC yoksa bile
    kart kabul edilir: gloss_en/register/ornekler saglamsa odenmis Ingilizce
    kart, ana dil karsiligi yuzunden REDDEDILEMEZ. Depodaki 43 reddin 21'i
    (looks_conjugated 14 + l1_ceviri_yapilmamis 4 + verb_missing_infinitive 3)
    tam olarak bu yuzden atilmisti."""
    result = qa_mod.run(GOOD_ANSWER, _unit())
    assert result.ok
    assert "gloss_l1" not in result.payload


def test_cevaptaki_gloss_l1_yuke_tasinmaz():
    """Model eski aliskanlikla `gloss_l1` dondurse bile QA onu TASIMAZ —
    depoya sizacak bir yol kalmasin."""
    result = qa_mod.run({**GOOD_ANSWER, "gloss_l1": "koşmak"}, _unit())
    assert result.ok
    assert "gloss_l1" not in result.payload


def test_qa_taninmayan_register_reddetmez_uyarir():
    result = qa_mod.run({**GOOD_ANSWER, "register": "sarkastik"}, _unit())
    assert result.ok
    assert result.payload["register"] == "neutral"
    assert "register_taninmadi" in result.reason


# --- Uctan uca kosu ------------------------------------------------------

def test_kart_butun_parcalariyla_tek_transactionda_yazilir():
    _seed_universe()
    result = _run(FakeProvider())
    assert result.approved == 1 and result.new_calls == 1

    conn = schema.open_lexicon_db()
    card = conn.execute("SELECT gloss_en, tier, status FROM sense_cards").fetchone()
    gloss_count = conn.execute(
        "SELECT COUNT(*) FROM sense_gloss_l1").fetchone()[0]
    examples = conn.execute("SELECT text FROM sense_examples ORDER BY seq").fetchall()
    level = conn.execute("SELECT cefr, freq_rank FROM item_level").fetchone()
    conn.close()

    assert card["gloss_en"] == GOOD_ANSWER["gloss_en"]
    assert (card["tier"], card["status"]) == (3, "approved")
    # Kartin parcasi ARTIK L1 DEGIL: o tablonun tek yazicisi LexiconL1EntryStore.
    assert gloss_count == 0
    assert len(examples) == 2
    assert tuple(level) == ("A1", 5)


def test_ikinci_kosuda_hic_odenmis_cagri_yapilmaz():
    """Adim 5'in artimlilik kabulu: ayni evren ikinci kez BEDAVADIR."""
    _seed_universe()
    _run(FakeProvider())

    provider = FakeProvider()
    second = _run(provider)
    assert second.plan.paid_calls == 0
    assert second.new_calls == 0
    assert provider.calls == []


def test_reddedilen_cevap_icerik_yazmaz_ama_satiri_kotu_isaretler():
    _seed_universe()
    _run(FakeProvider(answer={**GOOD_ANSWER,
                              "examples": ["I run every day.",
                                           "I  run every  day."]}))

    conn = schema.open_lexicon_db()
    card = conn.execute(
        "SELECT gloss_en, status, reject_reason FROM sense_cards").fetchone()
    assert conn.execute("SELECT COUNT(*) FROM sense_gloss_l1").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sense_examples").fetchone()[0] == 0
    conn.close()
    assert card["status"] == "rejected"
    assert card["reject_reason"] == "ornekler_ayni"
    # QA reddederse YUK BOS doner — kartin icerigi hic yazilmaz. Satir yalnizca
    # "burasi kotu" demek icin durur, onarim kosusu (`--redo bad`) onu bulur.
    assert card["gloss_en"] is None


def test_dry_run_tek_kurus_harcamaz():
    _seed_universe()
    provider = FakeProvider()
    result = _run(provider, dry_run=True)
    assert provider.calls == []
    assert result.new_calls == 0
    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT COUNT(*) FROM sense_cards").fetchone()[0] == 0
    conn.close()


def test_insan_satirina_model_dokunamaz():
    _seed_universe()
    store = LexiconCardStore()
    unit = units.load_units(TAG, L2)[0]
    store.save(JobContext(tag=TAG, l2=L2, l1=L1),
               WriteRequest(unit=unit,
                            payload={"gloss_en": "insan yazdi",
                                     "examples": []},
                            tier=TIER_HUMAN, model_label=None), None)
    store.commit()
    store.close()

    provider = FakeProvider()
    result = _run(provider)
    assert provider.calls == []                  # plan bile cagri istemedi
    assert result.plan.paid_calls == 0

    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT gloss_en FROM sense_cards").fetchone()[0] == "insan yazdi"
    conn.close()


# --- Dil simetrisi (Is 2b) ------------------------------------------------

def test_kart_kosusu_sense_gloss_l1e_tek_satir_yazmaz():
    """Model cevabi `gloss_l1` ICERSE ve kosunun bir `l1`i OLSA bile kart
    deposu o tabloya dokunmaz — bugunku davranisin tam tersi."""
    _seed_universe()
    result = _run(FakeProvider(answer={**GOOD_ANSWER, "gloss_l1": "koşmak"}))
    assert result.approved == 1

    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT COUNT(*) FROM sense_gloss_l1").fetchone()[0] == 0
    # Kartin kendisi normal sekilde yazildi — silinen sey yalnizca L1.
    assert conn.execute("SELECT COUNT(*) FROM sense_cards").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM sense_examples").fetchone()[0] == 2
    conn.close()


def test_sense_gloss_l1in_tek_yazicisi_gloss_deposudur():
    """KAYNAK DENETIMI: `modules/lexicon_card/` altinda `sense_gloss_l1`e
    yazan tek dosya `translate/store.py` olmali. Bu kural calisma zamaninda
    degil KAYNAKTA civilenir — ikinci bir yazici geri sizarsa test duser."""
    import os
    import re

    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "polyvo", "modules", "lexicon_card")
    # Yalnizca SATIR YAZAN ifadeler; `CREATE TABLE` (schema.py) yazma degildir.
    pattern = re.compile(
        r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+sense_gloss_l1"
        r"|UPDATE\s+sense_gloss_l1"
        r"|DELETE\s+FROM\s+sense_gloss_l1",
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
        "`sense_gloss_l1`e yazan dosyalar: " + ", ".join(sorted(writers)))
