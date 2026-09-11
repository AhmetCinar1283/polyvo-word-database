"""
Grammar not cevirisi kosusu testleri — HICBIR AG CAGRISI YOK.

Olculen sey Is 6 §18'in bilinen tuzagi: notun ICINDE kalan `trigger`in
Ingilizce hali, dil kapisi tarafindan "cevrilmemis" sanilip DOGRU bir
ceviriyi REDDETMEMELI. Ayrica: yalnizca ONAYLI paketler cevrilir,
`rule_id`/`trigger` cevrilmez, ikinci kosu 0 odenecek cagri, dil basina
BAGIMSIZ satirlar.
"""

from __future__ import annotations

import pytest

from grammar_helpers import (
    FakeProvider,
    GRAMMAR_TR_ANSWER,
    L2,
    TAG,
    grammar_answer,
    grammar_translate_answer,
    run_cloze,
    run_grammar,
    run_grammar_translate,
    seed_all,
)
from polyvo.core import paths
from polyvo.modules.grammar import schema
from polyvo.modules.grammar.translate import units as translate_units


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _prepared():
    """Onayli bir grammar paketi uretir — cevirinin girdisi budur."""
    seed_all()
    run_cloze(FakeProvider())
    run_grammar(FakeProvider(answer=grammar_answer()))


def _tr_status() -> tuple[str, str | None]:
    """`(status, reject_reason)` — tek satir varsayimiyla."""
    conn = schema.open_grammar_db()
    try:
        row = conn.execute(
            "SELECT status, reject_reason FROM"
            " sentence_grammar_translation").fetchone()
        return tuple(row)
    finally:
        conn.close()


def _counts() -> dict[str, int]:
    """Ceviri deposundaki tablo satir sayilari."""
    conn = schema.open_grammar_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("sentence_grammar_translation",
                             "sentence_grammar_rule_l1")}
    finally:
        conn.close()


# --- Girdi kapisi ------------------------------------------------------------

def test_yalnizca_onayli_paket_cevrilir():
    """Reddedilmis/uretilmemis grammar paketinin cevrilecek notu yoktur."""
    seed_all()
    run_cloze(FakeProvider())
    assert translate_units.load_units(TAG, L2) == []      # grammar hic kosmadi
    run_grammar(FakeProvider(answer=grammar_answer()))
    assert [u.key for u in translate_units.load_units(TAG, L2)] == [
        "cloze|en:bank:noun"]


# --- Uretim + depo -----------------------------------------------------------

def test_ceviri_bir_paket_bes_not_yazar():
    """1 grup basina 1 durum satiri + 5 kural notu (GRAMMAR_ANSWER: 1+2+2)."""
    _prepared()
    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))

    counts = _counts()
    assert counts["sentence_grammar_translation"] == 1
    assert counts["sentence_grammar_rule_l1"] == 5
    assert _tr_status()[0] == "approved"


def test_rule_id_ve_trigger_l1_tablosuna_hic_yazilmaz():
    """`sentence_grammar_rule_l1` yalnizca `note` tasir — `rule_id`/`trigger`
    icin sutun bile yoktur (Is 6 §18)."""
    _prepared()
    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))
    conn = schema.open_grammar_db()
    cols = [row[1] for row in conn.execute(
        "PRAGMA table_info(sentence_grammar_rule_l1)")]
    conn.close()
    assert "rule_id" not in cols
    assert "trigger" not in cols


def test_ceviri_kosusu_ingilizce_tabloya_dokunmaz():
    """`sentence_grammar_rule` cevirimeden once/sonra AYNI."""
    _prepared()
    conn = schema.open_grammar_db()
    before = conn.execute(
        "SELECT * FROM sentence_grammar_rule ORDER BY ref, rank").fetchall()
    conn.close()

    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))

    conn = schema.open_grammar_db()
    after = conn.execute(
        "SELECT * FROM sentence_grammar_rule ORDER BY ref, rank").fetchall()
    conn.close()
    assert after == before


def test_ikinci_kosu_sifir_odenecek_cagri():
    """Artimlilik: ayni dil ikinci kez kosuldugunda `paid_calls = 0`."""
    _prepared()
    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))
    second = FakeProvider(answer=grammar_translate_answer())
    result = run_grammar_translate(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


def test_bir_dil_digerinin_satirini_etkilemez():
    """`tr` ve `de` YAN YANA durur, biri otekini silmez."""
    _prepared()
    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))
    de_notes = [f"{n} (auf Deutsch, siehe Löffel usw.)"
               for n in GRAMMAR_TR_ANSWER["notes"]]
    run_grammar_translate(
        FakeProvider(answer=grammar_translate_answer(notes=de_notes)), l1="de")

    conn = schema.open_grammar_db()
    langs = [row[0] for row in conn.execute(
        "SELECT l1 FROM sentence_grammar_translation ORDER BY l1")]
    note_counts = conn.execute(
        "SELECT l1, COUNT(*) FROM sentence_grammar_rule_l1"
        " GROUP BY l1 ORDER BY l1").fetchall()
    conn.close()
    assert langs == ["de", "tr"]
    assert [tuple(row) for row in note_counts] == [("de", 5), ("tr", 5)]


# --- §18: bilinen tuzak -------------------------------------------------------

def test_notun_icinde_kalan_trigger_dogru_ceviriyi_reddetmez():
    """Kabul olcutu (§18): notun icindeki Ingilizce `trigger` ("keep",
    "to pay", "to ask" vb.), dil kapisi tarafindan 'cevrilmemis' sanilip
    REDDEDILMEMELI."""
    _prepared()
    run_grammar_translate(FakeProvider(answer=grammar_translate_answer()))
    assert _tr_status()[0] == "approved"
    conn = schema.open_grammar_db()
    notes = [row[0] for row in conn.execute(
        "SELECT note FROM sentence_grammar_rule_l1 WHERE l1 = 'tr'")]
    conn.close()
    # Kanit: cevrilen notlardan en az biri kendi trigger'inin Ingilizce
    # halini tasiyor ve yine de onaylandi.
    assert any("to pay" in n or "keep" in n or "to ask" in n for n in notes)


def test_ceviri_yapilmamis_not_reddedilir():
    """Not TAMAMEN Ingilizce kalirsa (ceviri yok) REDDEDILIR."""
    _prepared()
    en_notes = [r["note"] for r in
               sorted(translate_units.load_units(TAG, L2)[0].data["rules"],
                     key=lambda r: (r["ref"], r["rank"]))]
    bad = grammar_translate_answer(notes=en_notes)
    run_grammar_translate(FakeProvider(answer=bad))
    status, reason = _tr_status()
    assert status == "rejected"
    assert reason in ("ceviri_yapilmamis", "l1_ceviri_yapilmamis")


def test_not_sayisi_uyusmuyorsa_reddedilir():
    """Bestten farkli sayida not (bicim hatasi) REDDEDILIR."""
    _prepared()
    bad = grammar_translate_answer(notes=GRAMMAR_TR_ANSWER["notes"][:2])
    run_grammar_translate(FakeProvider(answer=bad))
    assert _tr_status() == ("rejected", "not_sayisi_uyusmuyor")
