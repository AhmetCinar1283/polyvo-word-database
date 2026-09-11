"""
Cloze ceviri kosusu testleri — HICBIR AG CAGRISI YOK.

Bu isin ayirt edici sozu §14'tur: CEVRILEN SEY CUMLEDIR, SIKLAR DEGIL.
Buradaki testler bunu iki yerden birden olcer: siklar prompta girmez ve
sema dile bagli degildir — besinci dil YENI SATIRDIR, sema degisikligi degil.
"""

from __future__ import annotations

import json

import pytest

from cloze_helpers import L2, TAG, FakeProvider, run_cloze, seed_all
from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.translate import units as tr_units
from polyvo.modules.cloze.translate.job import ClozeTranslationJob
from polyvo.modules.cloze.translate.store import ClozeTranslationStore

SENTENCES = [
    "I keep my money in a bank.",
    "She walked to the bank to pay the bill this morning.",
    "After the long meeting he went to the bank to ask about the new "
    "office rules and forms.",
]

TR = ["Param bir bankada duruyor.",
      "Bu sabah faturayi odemek icin bankaya yurudu.",
      "Uzun toplantidan sonra yeni ofis kurallarini sormak icin bankaya gitti."]


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _answer(sentences=None) -> dict:
    """Gecerli bir uc cumlelik ceviri cevabi."""
    return {"sentences": list(sentences or TR)}


def run_translate(provider, l1="tr", **kwargs):
    """Ceviri isini sahte saglayiciyla ucdan uca kosturur."""
    store = ClozeTranslationStore()
    try:
        return engine_run.run(
            ClozeTranslationJob(),
            JobContext(tag=TAG, l2=L2, l1=l1, variant=l1),
            provider=provider, store=store, assume_yes=True, **kwargs)
    finally:
        store.close()


def _rows(table: str) -> list[tuple]:
    """Ceviri tablosunun satirlari."""
    conn = schema.open_cloze_db()
    try:
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


def _prepared():
    """Onayli bir cloze paketi uretir — cevirinin girdisi budur."""
    seed_all()
    run_cloze(FakeProvider())


# --- Girdi kapisi ----------------------------------------------------------

def test_yalnizca_onayli_paket_cevrilir():
    """Reddedilmis/uretilmemis paketin cevrilecek cumlesi yoktur."""
    seed_all()
    assert tr_units.load_units(TAG, L2) == []      # henuz paket yok
    run_cloze(FakeProvider())
    assert [u.key for u in tr_units.load_units(TAG, L2)] == ["en:bank:noun"]


# --- §14: siklar cevrilmez -------------------------------------------------

def test_siklar_prompta_hic_girmez():
    """Kabul olcutu: celdiriciler ceviri promptunda GORUNMEZ."""
    _prepared()
    provider = FakeProvider(answer=_answer())
    run_translate(provider)

    assert len(provider.calls) == 1
    prompt = provider.calls[0]
    sentences = " ".join(SENTENCES)
    # Yalnizca CUMLELERDE GECMEYEN celdiriciler olculebilir: "office" gibi bir
    # kelime ucuncu cumlenin kendi metninde de gecer, orada bulunmasi mesrudur.
    for distractor in ("spoon", "cloud", "chair", "garden", "kitchen",
                       "forest", "market"):
        assert distractor not in sentences              # olcum gecerli mi
        assert distractor not in prompt, f"celdirici prompta sizdi: {distractor}"
    assert SENTENCES[0] in prompt                       # cumleler var


def test_ceviri_kosusu_sik_satirlarina_dokunmaz():
    """Siklar dile bagli DEGIL: ceviri kosusundan once ve sonra AYNI."""
    _prepared()
    before = _rows("sense_cloze_option")
    run_translate(FakeProvider(answer=_answer()))
    assert _rows("sense_cloze_option") == before
    assert len(before) == 12


def test_ceviri_uc_cumle_yazar():
    """Anlam basina dil basina 1 paket satiri + 3 cumle."""
    _prepared()
    run_translate(FakeProvider(answer=_answer()))

    conn = schema.open_cloze_db()
    try:
        status, l1 = conn.execute(
            "SELECT status, l1 FROM sense_cloze_translation").fetchone()[:2]
        sentences = [row[0] for row in conn.execute(
            "SELECT sentence FROM sense_cloze_translation_sentence"
            " WHERE l1 = 'tr' ORDER BY seq")]
    finally:
        conn.close()
    assert (status, l1) == ("approved", "tr")
    assert sentences == TR


# --- Cok dillilik ----------------------------------------------------------

def test_besinci_dil_sema_degistirmeden_planlanir():
    """Kabul olcutu: 5. dil YENI SATIRDIR — DDL'e tek karakter eklenmez."""
    _prepared()
    conn = schema.open_cloze_db()
    try:
        before = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table'"
            " ORDER BY name").fetchall()
    finally:
        conn.close()

    result = run_translate(FakeProvider(), l1="fr", dry_run=True)
    assert result.plan.paid_calls == 1          # fr planlanabiliyor

    conn = schema.open_cloze_db()
    try:
        after = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table'"
            " ORDER BY name").fetchall()
    finally:
        conn.close()
    assert after == before


def test_bir_dil_digerinin_satirini_etkilemez():
    """`tr` ve `de` ayni anlamda YAN YANA durur, biri otekini silmez."""
    _prepared()
    run_translate(FakeProvider(answer=_answer()))
    run_translate(FakeProvider(answer=_answer(["Mein Geld liegt auf einer Bank.",
                                               "Sie ging heute zur Bank.",
                                               "Er ging spaeter zur Bank."])),
                  l1="de")

    conn = schema.open_cloze_db()
    try:
        langs = [row[0] for row in conn.execute(
            "SELECT l1 FROM sense_cloze_translation ORDER BY l1")]
        counts = conn.execute(
            "SELECT l1, COUNT(*) FROM sense_cloze_translation_sentence"
            " GROUP BY l1 ORDER BY l1").fetchall()
    finally:
        conn.close()
    assert langs == ["de", "tr"]
    assert [tuple(row) for row in counts] == [("de", 3), ("tr", 3)]


def test_ikinci_kosu_sifir_odenecek_cagri():
    """Artimlilik: ayni dil ikinci kez kosuldugunda `paid_calls = 0`."""
    _prepared()
    run_translate(FakeProvider(answer=_answer()))
    second = FakeProvider(answer=_answer())
    result = run_translate(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


# --- QA --------------------------------------------------------------------

@pytest.mark.parametrize("sentences, expected", [
    (TR[:2], "cumle_sayisi_uyusmuyor"),
    ([TR[0], "", TR[2]], "bos_cumle"),
    (SENTENCES, "ceviri_yapilmamis"),
])
def test_ceviri_qa_kapilari(sentences, expected):
    """Sayilabilir hata REDDEDER; ceviri yapilmamissa satir yazilmaz."""
    _prepared()
    run_translate(FakeProvider(answer=_answer(sentences)))

    conn = schema.open_cloze_db()
    try:
        status, reason = conn.execute(
            "SELECT status, reject_reason FROM sense_cloze_translation"
        ).fetchone()[:2]
        written = conn.execute(
            "SELECT COUNT(*) FROM sense_cloze_translation_sentence"
        ).fetchone()[0]
    finally:
        conn.close()
    assert status == "rejected"
    assert reason == expected
    assert written == 0


# --- --force ---------------------------------------------------------------

def _tr_status() -> str:
    """Ceviri satirinin depodaki durumu."""
    conn = schema.open_cloze_db()
    try:
        return conn.execute(
            "SELECT status FROM sense_cloze_translation").fetchone()[0]
    finally:
        conn.close()


def test_force_self_ceviri_kosusunda_da_onbellegi_atlar():
    """`--force self` cloze CEVIRISINDE de ucdan uca calisir: rank kapisi
    acilir, onbellekteki bozuk ceviri bugunku QA'dan gecirilir (yine
    reddedilir), sonra onbellek ATLANARAK modelden taze cevap alinir."""
    _prepared()
    run_translate(FakeProvider(answer=_answer(TR[:2])))     # cumle sayisi eksik
    assert _tr_status() == "rejected"

    fixed = FakeProvider(answer=_answer())
    # --force olmadan ayni model bu satiri hic denemez.
    assert run_translate(fixed, redo="bad").plan.skipped() == {"skip_outranked": 1}
    assert fixed.calls == []

    result = run_translate(fixed, redo="bad", force="self")
    assert result.plan.paid_calls == 1      # zorlanan birim BEDAVA sayilmaz
    assert result.new_calls == 1            # onbellek atlandi, model arandi
    assert _tr_status() == "approved"
