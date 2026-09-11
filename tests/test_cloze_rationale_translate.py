"""
Cloze ipucu/aciklama ceviri kosusu testleri — HICBIR AG CAGRISI YOK.

Bu isin ayirt edici sozu Is 4 S14 (siklar cevrilmez) + Is 5 S16 (bilinen
tuzak): aciklamada gecen sikkin Ingilizce kelimesi CEVRILMEDEN kalir ve dil
kapisi bu yuzden DOGRU bir ceviriyi reddetmemelidir.
"""

from __future__ import annotations

import pytest

from cloze_helpers import (
    FakeProvider, RATIONALE_TR_ANSWER, TAG, L2, rationale_answer,
    rationale_translate_answer, run_cloze, run_rationale,
    run_rationale_translate, seed_all,
)
from polyvo.core import paths
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.rationale.translate import units as tr_units


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _prepared():
    """Onayli bir ipucu/aciklama paketi uretir — cevirinin girdisi budur."""
    seed_all()
    run_cloze(FakeProvider())
    run_rationale(FakeProvider(answer=rationale_answer()))


def _tr_status() -> tuple[str, str | None]:
    """`(status, reject_reason)` — tek satir varsayimiyla."""
    conn = schema.open_cloze_db()
    try:
        row = conn.execute(
            "SELECT status, reject_reason FROM"
            " sense_cloze_rationale_translation").fetchone()
        return tuple(row)
    finally:
        conn.close()


def _counts() -> dict[str, int]:
    """Ceviri deposundaki tablo satir sayilari."""
    conn = schema.open_cloze_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("sense_cloze_rationale_translation",
                             "sense_cloze_hint_l1",
                             "sense_cloze_option_reason_l1")}
    finally:
        conn.close()


# --- Girdi kapisi ------------------------------------------------------------

def test_yalnizca_onayli_rationale_cevrilir():
    """Reddedilmis/uretilmemis ipucu/aciklamanin cevrilecek metni yoktur."""
    seed_all()
    run_cloze(FakeProvider())
    assert tr_units.load_units(TAG, L2) == []          # rationale hic kosmadi
    run_rationale(FakeProvider(answer=rationale_answer()))
    assert [u.key for u in tr_units.load_units(TAG, L2)] == ["en:bank:noun"]


# --- Uretim + depo -----------------------------------------------------------

def test_ceviri_uc_ipucu_on_iki_aciklama_yazar():
    """Anlam basina dil basina 1 paket satiri + 3 ipucu + 12 aciklama."""
    _prepared()
    run_rationale_translate(FakeProvider(answer=rationale_translate_answer()))

    counts = _counts()
    assert counts["sense_cloze_rationale_translation"] == 1
    assert counts["sense_cloze_hint_l1"] == 3
    assert counts["sense_cloze_option_reason_l1"] == 12
    assert _tr_status()[0] == "approved"


def test_ceviri_kosusu_ingilizce_tablolara_dokunmaz():
    """`sense_cloze_hint`/`sense_cloze_option_reason` cevirimeden once/sonra
    AYNI — ceviri Ingilizce tarafi asla yazmaz."""
    _prepared()
    conn = schema.open_cloze_db()
    before_hints = conn.execute("SELECT * FROM sense_cloze_hint").fetchall()
    before_reasons = conn.execute(
        "SELECT * FROM sense_cloze_option_reason").fetchall()
    conn.close()

    run_rationale_translate(FakeProvider(answer=rationale_translate_answer()))

    conn = schema.open_cloze_db()
    after_hints = conn.execute("SELECT * FROM sense_cloze_hint").fetchall()
    after_reasons = conn.execute(
        "SELECT * FROM sense_cloze_option_reason").fetchall()
    conn.close()
    assert after_hints == before_hints
    assert after_reasons == before_reasons


def test_ikinci_kosu_sifir_odenecek_cagri():
    """Artimlilik: ayni dil ikinci kez kosuldugunda `paid_calls = 0`."""
    _prepared()
    run_rationale_translate(FakeProvider(answer=rationale_translate_answer()))
    second = FakeProvider(answer=rationale_translate_answer())
    result = run_rationale_translate(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


def test_besinci_dil_sema_degistirmeden_planlanir():
    """Kabul olcutu: 5. dil YENI SATIRDIR — DDL'e tek karakter eklenmez."""
    _prepared()
    conn = schema.open_cloze_db()
    before = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
        " ORDER BY name").fetchall()
    conn.close()

    result = run_rationale_translate(FakeProvider(), l1="fr", dry_run=True)
    assert result.plan.paid_calls == 1

    conn = schema.open_cloze_db()
    after = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table'"
        " ORDER BY name").fetchall()
    conn.close()
    assert after == before


def test_bir_dil_digerinin_satirini_etkilemez():
    """`tr` ve `de` ayni anlamda YAN YANA durur, biri otekini silmez."""
    _prepared()
    run_rationale_translate(FakeProvider(answer=rationale_translate_answer()))
    # Icerikten cok SAYIM onemli; umlaut, dil kapisinin `de` isaretcisini
    # (`LANG_MARKERS`) hemen tetiklesin diye her cumleye eklendi.
    de_reasons = [f"{r} (auf Deutsch, siehe Löffel usw.)"
                 for r in RATIONALE_TR_ANSWER["reasons"]]
    de_answer = rationale_translate_answer(
        hints=["Denke darüber nach, wo Leute ihr Geld sicher aufbewahren.",
              "Denke an ein Geschäft, das mit Geld und Rechnungen zu tun hat.",
              "Stelle dir vor, wo du nach Kontoinformationen fragen würdest."],
        reasons=de_reasons)
    run_rationale_translate(FakeProvider(answer=de_answer), l1="de")

    conn = schema.open_cloze_db()
    langs = [row[0] for row in conn.execute(
        "SELECT l1 FROM sense_cloze_rationale_translation ORDER BY l1")]
    hint_counts = conn.execute(
        "SELECT l1, COUNT(*) FROM sense_cloze_hint_l1"
        " GROUP BY l1 ORDER BY l1").fetchall()
    conn.close()
    assert langs == ["de", "tr"]
    assert [tuple(row) for row in hint_counts] == [("de", 3), ("tr", 3)]


# --- S16: bilinen tuzak ------------------------------------------------------

def test_sikkin_ingilizce_kelimesini_iceren_dogru_ceviri_onaylanir():
    """Kabul olcutu (S16): aciklamada KALAN Ingilizce sik kelimesi, dil
    kapisi tarafindan 'cevrilmemis' sanilip REDDEDILMEMELI."""
    _prepared()
    run_rationale_translate(FakeProvider(answer=rationale_translate_answer()))
    assert _tr_status()[0] == "approved"
    # Kanit: cevrilen aciklamalarin en az biri sikkin Ingilizce kelimesini
    # (ornegin "spoon") tasiyor ve yine de onaylandi.
    conn = schema.open_cloze_db()
    reasons = [row[0] for row in conn.execute(
        "SELECT reason FROM sense_cloze_option_reason_l1 WHERE l1 = 'tr'")]
    conn.close()
    assert any("spoon" in r.lower() for r in reasons)


def test_ceviri_yapilmamis_aciklama_reddedilir():
    """Aciklama TAMAMEN Ingilizce kalirsa (ceviri yok) REDDEDILIR."""
    _prepared()
    en_reasons = [
        r["reason"] for r in
        sorted(tr_units.load_units(TAG, L2)[0].data["reasons"],
              key=lambda r: (r["seq"], r["opt_seq"]))
    ]
    bad = rationale_translate_answer(reasons=en_reasons)
    run_rationale_translate(FakeProvider(answer=bad))
    status, reason = _tr_status()
    assert status == "rejected"
    assert reason in ("ceviri_yapilmamis", "l1_ceviri_yapilmamis")


def test_ipucu_sayisi_uyusmuyorsa_reddedilir():
    """Ucten farkli sayida ipucu (bicim hatasi) REDDEDILIR."""
    _prepared()
    bad = rationale_translate_answer(hints=RATIONALE_TR_ANSWER["hints"][:2])
    run_rationale_translate(FakeProvider(answer=bad))
    assert _tr_status() == ("rejected", "ipucu_sayisi_uyusmuyor")
