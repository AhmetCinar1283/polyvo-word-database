"""
`lexicon_card/note` testleri — HICBIR AG CAGRISI YOK: sahte saglayici gercek
motoru, gercek QA'yi ve gercek depoyu kullanir.

Olculen sey Is 3'un A boluminun kabul kriterleridir: `usage_note` KOSULLUDUR
(bos not red DEGILDIR), `gloss_en`in kopyasi/yeniden ifadesi REDDEDILIR,
kartsiz/onaysiz anlam birime girmez, kart bir daha ODENMEZ, ikinci kosuda
`paid_calls = 0`, `sense_cards`a tek satir yazilmaz.
"""

from __future__ import annotations

import json

import pytest

from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.llm.base import LLMResult
from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema
from polyvo.modules.lexicon_card.note import qa as qa_mod, units
from polyvo.modules.lexicon_card.note.job import LexiconNoteJob
from polyvo.modules.lexicon_card.note.store import LexiconNoteStore
from polyvo.modules.lexicon_card.store import LexiconCardStore

TAG, L2 = "test", "en"

CARD_ANSWER = {
    "gloss_en": "to move quickly on foot",
    "register": "neutral",
    "examples": ["I run every morning before work.",
                 "They ran across the empty field."],
}

NONE_ANSWER = {"reason": "none", "usage_note": ""}
IDIOM_ANSWER = {"reason": "idiom", "usage_note": "Also used to mean managing a business."}


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


class FakeProvider:
    """`complete_json` sozlesmesini taklit eden, agi olmayan saglayici."""

    def __init__(self, answer=None, label="cloudflare:@cf/qwen/qwen3-30b-a3b-fp8"):
        self.label = label
        self.answer = answer if answer is not None else NONE_ANSWER
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
    """`sense_cards`a ONAYLI bir kart yazar (usage_note KARTIN parcasi DEGIL)."""
    from polyvo.modules.lexicon_card import units as card_units

    unit = next(u for u in card_units.load_units(TAG, L2)
               if u.data["headword"] == headword and u.data["pos"] == pos)
    store = LexiconCardStore()
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload=answer or CARD_ANSWER, tier=3,
        model_label="cloudflare:@cf/qwen/qwen3-30b-a3b-fp8"), None)
    store.commit()
    store.close()


def _run(provider, **kwargs):
    """Motoru sahte saglayiciyla ucdan uca kosturur."""
    store = LexiconNoteStore()
    try:
        return engine_run.run(LexiconNoteJob(), JobContext(tag=TAG, l2=L2),
                              provider=provider, store=store, assume_yes=True,
                              **kwargs)
    finally:
        store.close()


# --- Birim yukleme -----------------------------------------------------

def test_kartsiz_anlam_birim_listesine_girmez():
    _seed_universe((("run", "verb", "A1", 5), ("apple", "noun", "A1", 9)))
    _seed_card("run", "verb")
    loaded = units.load_units(TAG, L2)
    assert [u.key for u in loaded] == ["en:run:verb"]


def test_onaysiz_kart_birim_listesine_girmez():
    from polyvo.modules.lexicon_card import units as card_units

    _seed_universe()
    unit = card_units.load_units(TAG, L2)[0]
    store = LexiconCardStore()
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload={}, status="rejected", tier=3,
        reject_reason="test_red", model_label="x"), None)
    store.commit()
    store.close()

    assert units.load_units(TAG, L2) == []


# --- QA kapisi: KOSULLULUK ------------------------------------------------

def test_sebep_none_bos_not_onaylanir():
    """En onemli kural: 'sebep yok + not bos' GECERLI onayli cevaptir."""
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    result = qa_mod.run(NONE_ANSWER, unit)
    assert result.ok
    assert result.payload == {"reason": "none", "note": ""}


def test_gecerli_sebep_ile_not_onaylanir():
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    result = qa_mod.run(IDIOM_ANSWER, unit)
    assert result.ok
    assert result.payload["reason"] == "idiom"
    assert result.payload["note"] == IDIOM_ANSWER["usage_note"]


def test_notu_tanimin_birebir_kopyasi_reddedilir():
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    result = qa_mod.run(
        {"reason": "idiom", "usage_note": CARD_ANSWER["gloss_en"]}, unit)
    assert not result.ok and result.reason == "not_tanimin_kopyasi"


def test_notu_tanimin_yeniden_ifadesi_reddedilir():
    """Kelime kumesi neredeyse ayni -> yeniden ifade, gercek bilgi yok."""
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    reworded = "quickly move on foot, to"
    result = qa_mod.run({"reason": "idiom", "usage_note": reworded}, unit)
    assert not result.ok and result.reason == "not_tanimin_yeniden_ifadesi"


def test_sebep_var_not_bos_bicim_hatasi_onarilir_reddetmez():
    """Sebep var ama not bos: bicim hatasi, para kaybi degil -> uyariyla onay."""
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    result = qa_mod.run({"reason": "idiom", "usage_note": ""}, unit)
    assert result.ok
    assert result.payload == {"reason": "none", "note": ""}
    assert "sebep_var_ama_not_bos_none_yazildi" in result.reason


def test_cevap_json_degilse_reddedilir():
    _seed_universe()
    _seed_card("run", "verb")
    unit = units.load_units(TAG, L2)[0]
    result = qa_mod.run(None, unit)
    assert not result.ok and result.reason == "cevap_json_degil"


# --- Uctan uca kosu ------------------------------------------------------

def test_dry_run_sifir_kart_uretimi():
    _seed_universe((("run", "verb", "A1", 5), ("go", "verb", "A1", 6)))
    _seed_card("run", "verb")
    _seed_card("go", "verb", answer={**CARD_ANSWER, "gloss_en": "to move",
                                     "examples": ["I go home.", "They go far."]})
    provider = FakeProvider()
    result = _run(provider, dry_run=True)
    assert result.plan.process_total == 2
    assert provider.calls == []
    assert result.new_calls == 0
    conn = schema.open_lexicon_db()
    assert conn.execute("SELECT COUNT(*) FROM sense_usage_note").fetchone()[0] == 0
    conn.close()


def test_bos_not_yazilir_kart_dokunulmadan_kalir():
    _seed_universe()
    _seed_card("run", "verb")
    result = _run(FakeProvider(answer=NONE_ANSWER))
    assert result.approved == 1 and result.new_calls == 1

    conn = schema.open_lexicon_db()
    row = conn.execute(
        "SELECT note, reason, status FROM sense_usage_note").fetchone()
    card = conn.execute("SELECT gloss_en, usage_note FROM sense_cards").fetchone()
    conn.close()
    assert row["note"] == "" and row["reason"] == "none" and row["status"] == "approved"
    # kart HIC dokunulmadi; usage_note sutunu artik hep NULL.
    assert card["gloss_en"] == CARD_ANSWER["gloss_en"]
    assert card["usage_note"] is None


def test_ikinci_kosuda_hic_odenmis_cagri_yapilmaz():
    _seed_universe()
    _seed_card("run", "verb")
    _run(FakeProvider(answer=NONE_ANSWER))

    provider = FakeProvider()
    second = _run(provider)
    assert second.plan.paid_calls == 0
    assert second.new_calls == 0
    assert provider.calls == []


def test_kosu_kart_tabloya_hic_yazmaz():
    """Kaynak denetimini calisma zamaninda da dogrular: `note` kosusu
    calistiktan sonra `sense_cards` satir sayisi/icerigi DEGISMEMIS olmali."""
    _seed_universe()
    _seed_card("run", "verb")
    conn = schema.open_lexicon_db()
    before = conn.execute("SELECT * FROM sense_cards").fetchall()
    conn.close()

    _run(FakeProvider(answer=IDIOM_ANSWER))

    conn = schema.open_lexicon_db()
    after = conn.execute("SELECT * FROM sense_cards").fetchall()
    conn.close()
    assert before == after


# --- Kaynak denetimi: tek yazici -----------------------------------------

def test_sense_usage_notea_yazan_tek_dosya_note_deposudur():
    """KAYNAK DENETIMI: `sense_usage_note`e yazan tek dosya `note/store.py`
    olmali. Kart deposunda ikinci bir yazici geri sizarsa test duser."""
    import os
    import re

    root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "polyvo", "modules", "lexicon_card")
    pattern = re.compile(
        r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+sense_usage_note"
        r"|UPDATE\s+sense_usage_note"
        r"|DELETE\s+FROM\s+sense_usage_note",
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

    assert sorted(writers) == ["note/store.py"], (
        "`sense_usage_note`e yazan dosyalar: " + ", ".join(sorted(writers)))
