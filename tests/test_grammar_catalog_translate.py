"""
Katalog aciklamasi cevirisi kosusu testleri — HICBIR AG CAGRISI YOK.

Olculen sey: birim CUMLE GRUBU degil KATALOGDAKI HER KURALDIR (kosu boyutu
katalogla orantili, ~60-80 cagri/dil, kulliyatla BUYUMEZ); `rule_id` ASLA
cevrilmez; ikinci kosu 0 odenecek cagri; insan `tier=0` satiri varken
model cagrisi istenmez.
"""

from __future__ import annotations

from grammar_helpers import (
    FakeProvider,
    catalog_translate_answer,
    run_catalog_translate,
)
from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.jobs.store.policy import TIER_HUMAN
from polyvo.modules.grammar import schema
from polyvo.modules.grammar.catalog import all_rules
from polyvo.modules.grammar.catalog_translate import units as ct_units
from polyvo.modules.grammar.catalog_translate.store import (
    GrammarCatalogTranslationStore,
)

import pytest


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _counts() -> dict[str, int]:
    """Ceviri deposundaki tablo satir sayilari."""
    conn = schema.open_grammar_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("grammar_catalog_translation", "grammar_rule_l1")}
    finally:
        conn.close()


# --- Birim boyutu -------------------------------------------------------------

def test_birim_sayisi_katalog_boyutuyla_orantili():
    """Kosu boyutu KATALOGDAKI kural sayisidir — kulliyata bagli DEGILDIR
    (cloze/rationale hic kosulmamis olsa da ayni sayidir)."""
    units = ct_units.load_units("herhangi-bir-tag", "en")
    assert len(units) == len(
        [r for r in all_rules() if r.merged_into is None])
    assert len(units) > 0


# --- Uretim + depo -----------------------------------------------------------

def test_ceviri_her_kurala_bir_satir_yazar():
    """Katalogdaki her (birlestirilmemis) kural icin 1 durum + 1 icerik satiri."""
    total = len(ct_units.load_units("t", "en"))
    result = run_catalog_translate(
        FakeProvider(answer=catalog_translate_answer()))
    assert result.plan.paid_calls == total

    counts = _counts()
    assert counts["grammar_catalog_translation"] == total
    assert counts["grammar_rule_l1"] == total


def test_rule_id_hic_cevrilmiyor_sutunda_yok():
    """`grammar_rule_l1`de `rule_id` DEGERI degismez (id sutunu, cevrilmez);
    `name`/`short` sutunlari ceviriyi tasir."""
    run_catalog_translate(FakeProvider(answer=catalog_translate_answer()))
    conn = schema.open_grammar_db()
    row = conn.execute(
        "SELECT rule_id, name, short FROM grammar_rule_l1 LIMIT 1").fetchone()
    conn.close()
    from polyvo.modules.grammar.catalog import get as catalog_get
    assert catalog_get(row["rule_id"]) is not None    # id KATALOGDA gecerli
    assert row["name"] == catalog_translate_answer()["name"]
    assert row["short"] == catalog_translate_answer()["short"]


def test_ikinci_kosu_sifir_odenecek_cagri():
    """Artimlilik: ayni dil ikinci kez kosuldugunda `paid_calls = 0`."""
    run_catalog_translate(FakeProvider(answer=catalog_translate_answer()))
    second = FakeProvider(answer=catalog_translate_answer())
    result = run_catalog_translate(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


def test_bir_dil_digerinin_satirini_etkilemez():
    """`tr` ve `de` YAN YANA durur, biri otekini silmez."""
    total = len(ct_units.load_units("t", "en"))
    run_catalog_translate(FakeProvider(answer=catalog_translate_answer()))
    run_catalog_translate(
        FakeProvider(answer=catalog_translate_answer(
            name="Gegenwart", short="Wird für Gewohnheiten benutzt (auf Deutsch).")),
        l1="de")

    conn = schema.open_grammar_db()
    langs = [row[0] for row in conn.execute(
        "SELECT l1 FROM grammar_catalog_translation GROUP BY l1 ORDER BY l1")]
    rule_l1_counts = conn.execute(
        "SELECT l1, COUNT(*) FROM grammar_rule_l1"
        " GROUP BY l1 ORDER BY l1").fetchall()
    conn.close()
    assert langs == ["de", "tr"]
    assert [tuple(row) for row in rule_l1_counts] == [
        ("de", total), ("tr", total)]


# --- Insan (tier=0) oncelikli ------------------------------------------------

def test_insan_tier_0_satiri_varken_cagri_istenmez():
    """Bir kural icin insan zaten `tier=0` ile yazmissa, o kural icin
    model cagrisi ISTENMEZ (kucuk tier kazanir)."""
    units = ct_units.load_units("t", "en")
    target = units[0]
    store = GrammarCatalogTranslationStore()
    ctx = JobContext(tag="t", l2="en", l1="tr", variant="tr")
    store._write_row(ctx, WriteRequest(
        unit=target, status="approved", reject_reason=None, tier=TIER_HUMAN,
        model_label="human", prompt_version="human",
        payload={"name": "İnsan Çevirisi", "short": "İnsan tarafından yazıldı."}))
    store.commit()
    store.close()

    result = run_catalog_translate(
        FakeProvider(answer=catalog_translate_answer()))
    assert result.plan.paid_calls == len(units) - 1

    conn = schema.open_grammar_db()
    row = conn.execute(
        "SELECT name FROM grammar_rule_l1 WHERE rule_id = ? AND l1 = 'tr'",
        (target.key,)).fetchone()
    conn.close()
    assert row["name"] == "İnsan Çevirisi"     # model UZERINE YAZMADI


# --- Icerik kapisi ------------------------------------------------------------

def test_ceviri_yapilmamis_reddedilir():
    """Isim/aciklama kaynagiyla AYNI kalirsa (ceviri yok) REDDEDILIR."""
    units = ct_units.load_units("t", "en")
    rule = units[0]
    bad = {"name": rule.data["name_en"], "short": rule.data["short_en"]}
    result = run_catalog_translate(FakeProvider(answer=bad), limit=1)
    assert result.plan.paid_calls == 1
    conn = schema.open_grammar_db()
    row = conn.execute(
        "SELECT status, reject_reason FROM grammar_catalog_translation"
        " WHERE rule_id = ?", (rule.key,)).fetchone()
    conn.close()
    assert row["status"] == "rejected"
    assert row["reject_reason"] == "ceviri_yapilmamis"
