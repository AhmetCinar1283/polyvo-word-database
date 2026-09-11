"""
Grammar analiz kosusu testleri — HICBIR AG CAGRISI YOK.

Olculen sey Is 6'nin kabul kriterleridir: uctan uca kosu, ikinci kosu 0
odenecek cagri, `--dry-run` 0 satir/0 kurus, `--propose-only` hic kural
satiri yazmiyor, cumle degisince grup BAYAT olur, onaylanmamis cloze paketi
grammar'a hic girmez, insan satiri (tier 0) varken cagri istenmez.
"""

from __future__ import annotations

import pytest

from grammar_helpers import (
    GRAMMAR_ANSWER,
    L2,
    TAG,
    FakeProvider,
    grammar_answer,
    run_grammar,
    seed_all,
)
from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.jobs.store.policy import TIER_HUMAN
from polyvo.modules.grammar import schema
from polyvo.modules.grammar import units as grammar_units
from polyvo.modules.grammar.store import GrammarStore


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))
    yield


def _seed_ready():
    """Onayli bir cloze paketi (dolayisiyla grammar'in girdisi) hazirlar."""
    from cloze_helpers import run_cloze
    seed_all()
    result = run_cloze(FakeProvider())
    assert result.plan.paid_calls == 1


def test_ucdan_uca_kosu_onaylanan_paket_yazar():
    _seed_ready()
    result = run_grammar(FakeProvider(answer=grammar_answer()))
    assert result.plan.paid_calls == 1

    conn = schema.open_grammar_db()
    try:
        row = conn.execute(
            "SELECT status FROM sentence_grammar").fetchone()
        assert row["status"] == "approved"
        rules = conn.execute(
            "SELECT ref, rank, rule_id, trigger FROM sentence_grammar_rule"
            " ORDER BY ref, rank").fetchall()
        assert len(rules) == 5             # 1 + 2 + 2 kural (GRAMMAR_ANSWER)
    finally:
        conn.close()


def test_ikinci_kosu_sifir_odenecek_cagri():
    _seed_ready()
    run_grammar(FakeProvider(answer=grammar_answer()))
    second = run_grammar(FakeProvider(answer=grammar_answer()))
    assert second.plan.paid_calls == 0


def test_dry_run_hicbir_sey_yazmaz():
    _seed_ready()
    provider = FakeProvider(answer=grammar_answer())
    run_grammar(provider, dry_run=True)
    assert provider.calls == []
    conn = schema.open_grammar_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) c FROM sentence_grammar").fetchone()["c"]
        assert count == 0
    finally:
        conn.close()


def test_propose_only_kural_satiri_yazmaz():
    _seed_ready()
    result = run_grammar(FakeProvider(answer=grammar_answer()),
                         propose_only=True)
    assert result.plan.paid_calls == 1
    conn = schema.open_grammar_db()
    try:
        assert conn.execute(
            "SELECT COUNT(*) c FROM sentence_grammar").fetchone()["c"] == 0
        assert conn.execute(
            "SELECT COUNT(*) c FROM sentence_grammar_rule"
        ).fetchone()["c"] == 0
    finally:
        conn.close()


def test_propose_only_adaylar_yazilir():
    _seed_ready()
    answer = grammar_answer()
    answer["sentences"][0]["candidates"] = [
        {"proposed_name": "Some new pattern", "trigger": "keep",
         "rationale": "not in catalog"}]
    run_grammar(FakeProvider(answer=answer), propose_only=True)
    conn = schema.open_grammar_db()
    try:
        rows = conn.execute(
            "SELECT proposed_name, status FROM grammar_candidate").fetchall()
        assert len(rows) == 1
        assert rows[0]["status"] == "new"
    finally:
        conn.close()


def test_cumle_degisince_grup_bayat_olur():
    """Onayli cumle metni degisince eski grammar satiri ARTIK bayattir —
    yeniden islenebilir sayilir (motora tek satir dokunulmaz)."""
    _seed_ready()
    run_grammar(FakeProvider(answer=grammar_answer()))

    store = GrammarStore()
    existing_before = store.load_existing(JobContext(tag=TAG, l2=L2))
    store.close()
    assert len(existing_before) == 1

    # Cloze cumlesini insan tarafindan degistir (bayatlik kaynagi).
    from polyvo.modules.cloze import schema as cloze_schema
    conn = cloze_schema.open_cloze_db()
    with conn:
        conn.execute(
            "UPDATE sense_cloze_question SET sentence = ? WHERE seq = 1",
            ("I always keep my money in a big red bank.",))
    conn.close()

    store2 = GrammarStore()
    existing_after = store2.load_existing(JobContext(tag=TAG, l2=L2))
    store2.close()
    assert existing_after == {}            # bayat satir donen sozluge HIC KONMAZ


def test_onaylanmamis_cloze_paketi_grammara_girmez():
    """Cloze kosulmadan grammar birim uretmez — onun analiz edecek onayli
    bir cumlesi yoktur."""
    from cloze_helpers import seed_universe, seed_card, seed_build_cefr
    seed_universe()
    seed_card()
    seed_build_cefr()
    # `run_cloze` HIC cagrilmadi: onayli cloze paketi yok.
    units = grammar_units.load_units(TAG, L2)
    assert units == []


def test_insan_satiri_varken_cagri_istenmez():
    """Tier 0 (insan) satir varken ikinci kosu bu birim icin cagri yapmaz."""
    _seed_ready()
    conn = schema.open_grammar_db()
    units = grammar_units.load_units(TAG, L2)
    unit = units[0]
    with conn:
        conn.execute(
            "INSERT INTO sentence_grammar (owner, group_key, status,"
            " tier, source, source_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (unit.data["owner"], unit.data["group_key"], "approved",
             TIER_HUMAN, "human", unit.data["source_sha256"]))
    conn.close()

    result = run_grammar(FakeProvider(answer=grammar_answer()))
    assert result.plan.paid_calls == 0
