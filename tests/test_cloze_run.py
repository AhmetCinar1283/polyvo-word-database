"""
Cloze uretim kosusu testleri — HICBIR AG CAGRISI YOK: sahte saglayici gercek
motoru, gercek QA'yi ve gercek depoyu kullanir.

Olculen sey Is 4'un kabul kriterleridir: `--dry-run` tek satir yazmaz,
ikinci kosu sifir cagri odetir, kartsiz/onaysiz anlam kosuya girmez, insan
satiri (tier 0) cagri istemez, reddedilen paket ICERIK yazmaz.
"""

from __future__ import annotations

import copy
from unittest import mock

import pytest

from cloze_helpers import (
    L2, MODEL, TAG, FakeProvider, cloze_answer, run_cloze, seed_all, seed_card,
    seed_universe,
)
from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.jobs.store.policy import TIER_HUMAN
from polyvo.modules.cloze import schema, units
from polyvo.modules.cloze.store import ClozeStore


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _status() -> str:
    """Cloze paketinin depodaki durumu."""
    conn = schema.open_cloze_db()
    try:
        return conn.execute("SELECT status FROM sense_cloze").fetchone()[0]
    finally:
        conn.close()


def _counts() -> dict[str, int]:
    """Cloze deposundaki tablo satir sayilari."""
    conn = schema.open_cloze_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("sense_cloze", "sense_cloze_question",
                             "sense_cloze_option")}
    finally:
        conn.close()


# --- Birim yukleme ---------------------------------------------------------

def test_kartsiz_anlam_birim_listesine_girmez():
    """Kartsiz anlamin soracak bir ANLAMI yoktur."""
    seed_universe((("bank", "noun", "A2", 5), ("apple", "noun", "A1", 9)))
    seed_card("bank", "noun")
    assert [u.key for u in units.load_units(TAG, L2)] == ["en:bank:noun"]


def test_icerik_sozcugu_olmayan_anlam_birim_listesine_girmez():
    """Edat/tanimlik/baglac cloze'a uygun degildir (`units.CLOZE_POS`):
    "the" 15-25 kelimelik bir cumlede TAM BIR KEZ gecemez, WordNet'te bu
    turler yoktur (celdirici turu olculemez), ve bir edatin coktan secmeli
    boslugu kelime bilgisi degil dilbilgisi sorusudur."""
    seed_universe((("bank", "noun", "A2", 5), ("the", "det", "A1", 1),
                   ("of", "prep", "A1", 2)))
    seed_card("bank", "noun")
    seed_card("the", "det")
    seed_card("of", "prep")
    assert [u.key for u in units.load_units(TAG, L2)] == ["en:bank:noun"]


def test_zarf_etiketli_edat_birim_listesine_girmez():
    """POS ETIKETI YETMEZ: sozluk "above"/"in"/"after"yi `adv`, "it"yi `noun`
    etiketler ve `CLOZE_POS` filtresinden gecerler. 2026-09-07 kosusunda
    basarisiz 16 birimin 7'si buydu; "it" YANLISLIKLA ONAYLANMISTI."""
    seed_universe((("bank", "noun", "A2", 5), ("above", "adv", "A1", 1),
                   ("it", "noun", "A1", 2), ("non", "adv", "A1", 3)))
    for headword, pos in (("bank", "noun"), ("above", "adv"), ("it", "noun"),
                          ("non", "adv")):
        seed_card(headword, pos)
    assert [u.key for u in units.load_units(TAG, L2)] == ["en:bank:noun"]


def test_kapali_sinif_sozcugun_icerik_kullanimi_birim_olur():
    """`can` (teneke kutu) ve `will` (irade) GERCEK isimlerdir — kelime
    duzeyindeki kara liste onlari kaybetmemeli, ayirt eden sey POS'tur."""
    seed_universe((("can", "noun", "A2", 1), ("can", "modal", "A1", 2)))
    seed_card("can", "noun")
    seed_card("can", "modal")
    assert [u.key for u in units.load_units(TAG, L2)] == ["en:can:noun"]


def test_yuksek_frekansli_icerik_fiili_birim_olmaya_devam_eder():
    """Kara liste `ENGLISH_MARKERS`tan TURETILMEDI: o liste dil tespiti icin
    genistir ve "take"/"go"/"know" gibi tam da ogretilecek A1 fiillerini
    icerir. Onlarin evrende kalmasi bu kararin OLCUSUDUR."""
    rows = tuple((w, "verb", "A1", i) for i, w in
                 enumerate(("take", "make", "go", "see", "know", "want",
                            "need", "look", "have", "do"), start=1))
    seed_universe(rows)
    for headword, pos, _, _ in rows:
        seed_card(headword, pos)
    keys = {u.key for u in units.load_units(TAG, L2)}
    assert keys == {f"en:{w}:verb" for w, _, _, _ in rows}


def test_onaysiz_kart_birim_listesine_girmez():
    """Reddedilmis kartin uzerine icerik uretilmez."""
    seed_universe()
    seed_card(status="rejected")
    assert units.load_units(TAG, L2) == []


# --- Kosu davranisi --------------------------------------------------------

def test_dry_run_tek_cagri_yapmaz_ve_tek_satir_yazmaz():
    """Kabul olcutu: `--dry-run` tek kurus harcamaz VE tek satir yazmaz."""
    seed_all()
    provider = FakeProvider()
    result = run_cloze(provider, dry_run=True)
    assert provider.calls == []
    assert result.plan.paid_calls == 1
    assert _counts() == {"sense_cloze": 0, "sense_cloze_question": 0,
                         "sense_cloze_option": 0}


def test_kosu_uc_soru_ve_on_iki_sik_yazar():
    """Anlam basina tam 3 soru, her soruda tam 4 sik."""
    seed_all()
    run_cloze(FakeProvider())
    assert _counts() == {"sense_cloze": 1, "sense_cloze_question": 3,
                         "sense_cloze_option": 12}

    conn = schema.open_cloze_db()
    try:
        rows = conn.execute(
            "SELECT seq, difficulty FROM sense_cloze_question ORDER BY seq"
        ).fetchall()
        answers = conn.execute(
            "SELECT seq, COUNT(*) FROM sense_cloze_option WHERE is_answer = 1"
            " GROUP BY seq").fetchall()
    finally:
        conn.close()
    assert [d for _seq, d in rows] == ["kolay", "orta", "zor"]
    assert [n for _seq, n in answers] == [1, 1, 1]      # tam 1 dogru cevap


def test_ikinci_kosu_sifir_odenecek_cagri(capsys):
    """Kabul olcutu (artimlilik): ikinci kosuda `paid_calls = 0`."""
    seed_all()
    first = FakeProvider()
    run_cloze(first)
    assert len(first.calls) == 1

    second = FakeProvider()
    result = run_cloze(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


def test_insan_satiri_icin_cagri_istenmez():
    """Kabul olcutu: tier 0 varken o birim icin cagri ISTENMEZ."""
    seed_all()
    unit = units.load_units(TAG, L2)[0]
    store = ClozeStore()
    human = {"questions": [dict(question, seq=seq) for seq, question
                           in enumerate(cloze_answer()["questions"], start=1)]}
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload=human, tier=TIER_HUMAN, model_label=None), None)
    store.commit()
    store.close()

    provider = FakeProvider()
    result = run_cloze(provider, dry_run=True)
    assert result.plan.paid_calls == 0
    assert provider.calls == []


def test_reddedilen_paket_icerik_yazmaz():
    """Reddedilen satir yalnizca `status`/`reject_reason` ile durur."""
    seed_all()
    broken = copy.deepcopy(cloze_answer())
    broken["questions"][0]["options"] = ["bank", "banks", "cloud", "chair"]
    run_cloze(FakeProvider(answer=broken))

    counts = _counts()
    assert counts["sense_cloze"] == 1
    assert counts["sense_cloze_question"] == 0
    assert counts["sense_cloze_option"] == 0

    conn = schema.open_cloze_db()
    try:
        status, reason = conn.execute(
            "SELECT status, reject_reason FROM sense_cloze").fetchone()
    finally:
        conn.close()
    assert status == "rejected"
    assert reason == "celdirici_hedef_kelimenin_bicimi"


def test_force_self_onbellegi_atlayip_reddedilen_paketi_duzeltir():
    """`--force self` cloze'da da UCTAN UCA calisir: rank kapisi acilir,
    onbellekteki bozuk cevap once bugunku QA'dan gecirilir (reddedilir),
    sonra ONBELLEK ATLANARAK modelden taze cevap alinir ve satir duzelir."""
    seed_all()
    broken = copy.deepcopy(cloze_answer())
    broken["questions"][0]["options"] = ["bank", "banks", "cloud", "chair"]
    run_cloze(FakeProvider(answer=broken))
    assert _status() == "rejected"

    # AYNI model, ama artik saglayici duzgun cevap veriyor. --force olmadan
    # rank kapisi bu satiri hic denemez.
    fixed = FakeProvider(answer=cloze_answer())
    assert run_cloze(fixed, redo="bad").plan.skipped() == {"skip_outranked": 1}
    assert fixed.calls == []

    result = run_cloze(fixed, redo="bad", force="self")
    assert result.plan.paid_calls == 1     # zorlanan birim BEDAVA sayilmaz
    assert result.new_calls == 1           # onbellek atlandi, model arandi
    assert len(fixed.calls) == 1
    assert _status() == "approved"
    assert _counts()["sense_cloze_question"] == 3


def test_force_self_gevsemis_qa_ile_cloze_satirini_cagrisiz_kurtarir():
    """Yeni QA eski cevabi kabul ediyorsa cloze satiri da tek kurus
    odenmeden onaylanir — birinci asama cloze'da da isliyor."""
    seed_all()
    broken = copy.deepcopy(cloze_answer())
    broken["questions"][0]["options"] = ["bank", "banks", "cloud", "chair"]
    run_cloze(FakeProvider(answer=broken))
    assert _status() == "rejected"

    # QA'daki hata duzeltildi: celdirici kontrolu artik bu satiri gecirir.
    from polyvo.modules.cloze.qa import distractor
    with mock.patch.object(distractor, "check", lambda questions, unit: (None, [])):
        provider = FakeProvider(answer=cloze_answer())
        result = run_cloze(provider, redo="bad", force="self")

    assert result.plan.skipped()["skip_revalidated"] == 1
    assert result.new_calls == 0           # HICBIR dis cagri yok
    assert provider.calls == []
    assert _status() == "approved"


def test_onayli_pakette_uyarilar_saklanir():
    """QA'nin olcemedigi sey kaybolmamali: uyarilar `warnings` sutununda."""
    seed_all()
    run_cloze(FakeProvider())
    conn = schema.open_cloze_db()
    try:
        status, warnings = conn.execute(
            "SELECT status, warnings FROM sense_cloze").fetchone()
    finally:
        conn.close()
    assert status == "approved"
    assert "celdiricinin_uymadigi_dogrulanamadi" in warnings


def test_ayni_birim_iki_kez_planlandiginda_ayni_prompt_uretilir():
    """Sahne kisiti deterministik oldugu icin prompt da deterministiktir —
    yoksa onbellek hicbir zaman tutmazdi."""
    from polyvo.modules.cloze.job import ClozeJob

    seed_all()
    job = ClozeJob()
    ctx = JobContext(tag=TAG, l2=L2)
    first = job.build_prompt(job.load_units(ctx)[0])
    second = job.build_prompt(job.load_units(ctx)[0])
    assert first == second


def test_kart_deposuna_tek_satir_yazilmaz():
    """Cloze OKUR, yazmaz: `lexicon.sqlite` kosudan once ve sonra AYNI."""
    from polyvo.modules.lexicon_card import schema as lexicon_schema

    seed_all()

    def snapshot():
        """Kart deposundaki tablo satir sayilari."""
        conn = lexicon_schema.open_lexicon_db()
        try:
            return {name: conn.execute(
                        f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                    for name in ("sense_cards", "sense_examples",
                                 "sense_gloss_l1", "sense_usage_note")}
        finally:
            conn.close()

    before = snapshot()
    run_cloze(FakeProvider())
    assert snapshot() == before
