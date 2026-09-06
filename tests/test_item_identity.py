"""
Katman 2a kabul testi (MIGRATION-PLAN §7, Adim 4):

  "workspace/ tamamen silinip yeniden uretildiginde item_id ve sense_id
  BIREBIR AYNI cikar."

Ayrica: `universe.py`'nin SAF secim/kapi mantigi ve `read_candidates`'in
POS'suz satirlari nasil elediği ayri ayri olculur.

Tum dosya yollari `paths.data_root`'u `tmp_path`'e cevirerek izole edilir —
gercek `data/` dizinine ASLA dokunulmaz.
"""

from __future__ import annotations

import os

import pytest

from polyvo.core import paths
from polyvo.core.jobs import schema as job_schema
from polyvo.curriculum import items, schema as cur_schema, universe
from polyvo.curriculum.commands import select_command
from polyvo.dictionary.build import schema as dict_schema, stages as dict_stages


TAG = "t1"
L2 = "en"


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Butun `data/` yollarini `tmp_path` altina yonlendirir (bkz. modul docstring'i)."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))
    return tmp_path


def _write_candidates(rows: list[tuple]) -> str:
    """Kucuk bir `lexicon.sqlite` kurar. `rows`: (headword, pos, cefr, freq_rank)."""
    db_path = dict_stages.lexicon_db_path(TAG)
    from polyvo.core import sqlite as sq
    conn = sq.connect(db_path, ddl=dict_schema.DDL)
    try:
        with conn:
            conn.executemany(
                "INSERT INTO candidates (headword, pos, tier, cefr, freq_rank,"
                " is_multiword, sources, pos_source) VALUES (?,?,1,?,?,0,'test',?)",
                [(h, p, c, f, "test" if p else None) for h, p, c, f in rows])
    finally:
        conn.close()
    return db_path


# ── universe.py: saf secim + kapi ──────────────────────────────────────────

def test_select_universe_frekansa_gore_siralar_ve_keser():
    cands = [
        universe.Candidate("zzz", "noun", None, 1),
        universe.Candidate("bank", "noun", "A1", 5),
        universe.Candidate("cat", "noun", "A1", 2),
    ]
    sel = universe.select_universe(cands, target_size=2)
    assert [c.headword for c in sel.kept] == ["zzz", "cat"]
    assert sel.excluded_over_target == 1
    assert sel.size == 2


def test_select_universe_bos_hedef_kapida_patlar():
    with pytest.raises(universe.UniverseError):
        universe.gate(universe.select_universe([], target_size=5))


def test_select_universe_target_size_gecersiz():
    with pytest.raises(ValueError):
        universe.select_universe([], target_size=0)


def test_read_candidates_possuz_satiri_eler_ve_sayar():
    db_path = _write_candidates([
        ("bank", "noun", "A1", 1),
        ("bank", "verb", "A2", 2),
        ("orphan", None, None, None),   # pos cozulememis (K7)
    ])
    kept, missing = universe.read_candidates(db_path)
    assert {(c.headword, c.pos) for c in kept} == {("bank", "noun"), ("bank", "verb")}
    assert missing == 1


def test_read_candidates_gecersiz_dosyada_kapi_patlar(tmp_path):
    bad = tmp_path / "bozuk.sqlite"
    bad.write_text("bu bir sqlite degil")
    with pytest.raises(universe.UniverseError):
        universe.read_candidates(str(bad))


# ── items.py: kimlik tahsisi + idempotentlik ───────────────────────────────

def _run_pipeline(target_size: int = 10) -> list[items.ProjectedItem]:
    """`select_command.cmd_select`'in yaptigi ile ayni sirayla, ama dogrudan
    fonksiyonlari cagirarak tek bir 'select' kosusu calistirir."""
    db_path = dict_stages.lexicon_db_path(TAG)
    kept, missing = universe.read_candidates(db_path)
    sel = universe.select_universe(kept, target_size=target_size, pos_missing_count=missing)
    universe.gate(sel)
    conn = cur_schema.open_identity_db()
    try:
        projected = items.assign_identities(conn, L2, sel.kept)
    finally:
        conn.close()
    items.write_workspace(TAG, L2, projected)
    return projected


def test_workspace_silinip_yeniden_uretilince_kimlikler_ayni_cikar():
    _write_candidates([
        ("bank", "noun", "A1", 1),
        ("bank", "verb", "A2", 2),
        ("cat", "noun", "A1", 3),
    ])

    first = _run_pipeline()
    ws_path = cur_schema.universe_db_path(TAG, L2)
    assert os.path.exists(ws_path)

    # "workspace/ tamamen silinip yeniden uretildiginde" — sadece workspace
    # silinir, data/stores/identity.sqlite (KUTSAL) dokunulmaz.
    os.remove(ws_path)
    second = _run_pipeline()

    by_key_first = {p.stable_key: (p.item_id, p.sense_id) for p in first}
    by_key_second = {p.stable_key: (p.item_id, p.sense_id) for p in second}
    assert by_key_first == by_key_second


def test_identity_sqlite_de_silinse_siralama_ayni_kimligi_uretir():
    """Daha guclu versiyon: `identity.sqlite` de silinirse (tam sifirdan),
    SIRALAMA deterministik oldugu icin tahsis yine BIREBIR ayni cikar."""
    _write_candidates([
        ("bank", "noun", "A1", 1),
        ("bank", "verb", "A2", 2),
        ("cat", "noun", "A1", 3),
    ])

    first = _run_pipeline()
    os.remove(cur_schema.universe_db_path(TAG, L2))
    os.remove(job_schema.identity_path())

    second = _run_pipeline()

    by_key_first = {p.stable_key: (p.item_id, p.sense_id) for p in first}
    by_key_second = {p.stable_key: (p.item_id, p.sense_id) for p in second}
    assert by_key_first == by_key_second


def test_ikinci_kosuda_ayni_headword_yeni_kimlik_almaz():
    """`items.assign_identities` cagrisi TEK BASINA da idempotenttir —
    workspace'e hic yazmadan iki kez cagrilsa bile."""
    _write_candidates([("bank", "noun", "A1", 1)])
    kept, _ = universe.read_candidates(dict_stages.lexicon_db_path(TAG))

    conn = cur_schema.open_identity_db()
    try:
        first = items.assign_identities(conn, L2, kept)
        second = items.assign_identities(conn, L2, kept)
    finally:
        conn.close()

    assert first == second


# ── uctan uca: `polyvo curriculum select` komutu ───────────────────────────

def test_cmd_select_dosyalari_yazar_ve_kilidi_raporlar():
    _write_candidates([
        ("bank", "noun", "A1", 1),
        ("bank", "verb", "A2", 2),
        ("cat", "noun", "A1", 3),
    ])
    args = _namespace(tag=TAG, l2=L2, target_size=2)
    code = select_command.cmd_select(args)
    assert code == 0

    ws_path = cur_schema.universe_db_path(TAG, L2)
    lock_path = paths.source_config_path(TAG, L2)
    assert os.path.exists(ws_path)
    assert os.path.exists(lock_path)

    import json
    with open(lock_path, encoding="utf-8") as fh:
        lock = json.load(fh)
    assert lock["universe_size"] == 2
    assert lock["tag"] == TAG


def test_cmd_select_bos_evrende_hicbir_dosya_yazmadan_1_doner():
    _write_candidates([("orphan", None, None, None)])   # tek satir, POS'suz
    args = _namespace(tag=TAG, l2=L2, target_size=5)
    code = select_command.cmd_select(args)
    assert code == 1
    assert not os.path.exists(cur_schema.universe_db_path(TAG, L2))
    assert not os.path.exists(paths.source_config_path(TAG, L2))


class _namespace:
    """`argparse.Namespace` yerine gecen minimal sahte — testte argparse kurmaya gerek yok."""

    def __init__(self, **kw):
        self.__dict__.update(kw)
