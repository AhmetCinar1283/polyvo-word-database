"""
`delivery` testleri — sevkiyatin iki sozu olculur:

  1. KAPI ONCE CALISIR: ihlalde SIFIR dosya yazilir, onceki sevkiyat bozulmaz.
  2. Uretilen dosyalar butundur ve DETERMINISTIKTIR (ayni girdi, ayni bayt).

Hicbir ag/LLM cagrisi yok: depo ve evren elle kurulur.
"""

from __future__ import annotations

import json
import os
import sqlite3

import pytest

from polyvo.core import paths
from polyvo.curriculum import schema as curriculum_schema
from polyvo.delivery import collect, gate, materialize, schema, snapshot, verify
from polyvo.modules.lexicon_card import schema as lexicon_schema

TAG, L2, L1 = "test", "en", "tr"

#: (headword, pos, cefr, freq_rank, status, kaynak)
WORDS = [
    ("run", "verb", "A1", 5, "approved", "llm"),
    ("apple", "noun", "A1", 9, "approved", "llm"),
    ("gibberish", "noun", "C2", 90, "rejected", "llm"),
]


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _seed(words=WORDS, l1=L1):
    """Evren + kimlik + odenmis depoyu testin bekledigi hale getirir."""
    universe = curriculum_schema.open_universe_db(TAG, L2)
    with universe:
        universe.executemany(
            "INSERT INTO universe_items (item_id, sense_id, l2, headword, pos,"
            " cefr, freq_rank, stable_key) VALUES (?,?,?,?,?,?,?,?)",
            [(i, 1000 + i, L2, head, pos, cefr, rank, f"{L2}:{head}:{pos}")
             for i, (head, pos, cefr, rank, _st, _src) in enumerate(words, start=1)])
    universe.close()

    identity = curriculum_schema.open_identity_db()
    with identity:
        identity.executemany(
            "INSERT INTO items (item_id, l2, headword, pos, stable_key)"
            " VALUES (?,?,?,?,?)",
            [(i, L2, head, pos, f"{L2}:{head}:{pos}")
             for i, (head, pos, *_rest) in enumerate(words, start=1)])
        identity.executemany(
            "INSERT INTO senses (sense_id, item_id, sense_ordinal, is_primary)"
            " VALUES (?,?,1,1)",
            [(1000 + i, i) for i in range(1, len(words) + 1)])
    identity.close()

    store = lexicon_schema.open_lexicon_db()
    with store:
        for i, (head, pos, _cefr, _rank, status, source) in enumerate(words, start=1):
            sense_id = 1000 + i
            store.execute(
                "INSERT INTO sense_cards (sense_id, item_id, stable_key, gloss_en,"
                " register, usage_note, tier, status, source, model)"
                " VALUES (?,?,?,?,?,?,3,?,?,'m')",
                (sense_id, i, f"{L2}:{head}:{pos}",
                 None if status != "approved" else f"tanim: {head}",
                 "neutral", "", status, source))
            if status != "approved":
                continue
            store.execute(
                "INSERT INTO sense_gloss_l1 (sense_id, l1, gloss, tier, source)"
                " VALUES (?,?,?,3,?)", (sense_id, l1, f"{head}-tr", source))
            store.executemany(
                "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
                " VALUES (?,?,?,3,?)",
                [(sense_id, seq, f"{head} ornek {seq}.", source) for seq in (1, 2)])
            store.execute(
                "INSERT INTO item_phonetics (item_id, variant, ipa, source)"
                " VALUES (?,'us',?,'dictionary_seed')", (i, f"/{head}/"))
    store.close()


def _dist(name):
    """Sevkiyat dizinindeki bir dosyanin tam yolu."""
    return os.path.join(paths.dist_dir(TAG, L2), name)


# --- Toplama + kapi -----------------------------------------------------

def test_yalnizca_onaylanmis_kartlar_sevk_edilir():
    _seed()
    shipment = collect.collect(TAG, L2, L1)
    assert [r.headword for r in shipment.rows] == ["run", "apple"]
    assert shipment.skipped_not_approved == 1


def test_ipa_kaynagi_metin_kapisina_girmez():
    """IPA bir OLGUDUR: `dictionary_seed`ten gelmesi kapiyi dusurmez."""
    _seed()
    shipment = collect.collect(TAG, L2, L1)
    assert shipment.rows[0].ipa == "/run/"
    assert shipment.rows[0].text_sources == {"llm"}
    assert gate.check(shipment) == []


def test_sevk_edilemez_kaynaktan_metin_kapiyi_dusurur():
    _seed(words=[("run", "verb", "A1", 5, "approved", "legacy_dist")])
    violations = gate.check(collect.collect(TAG, L2, L1))
    assert [v.rule for v in violations] == ["sevk_edilemez_kaynaktan_metin"]


def test_kapi_ihlalinde_hicbir_dosya_yazilmaz():
    _seed(words=[("run", "verb", "A1", 5, "approved", "legacy_dist")])
    with pytest.raises(gate.ShipGateError):
        materialize.run(TAG, L2, L1)
    assert not os.path.exists(paths.dist_dir(TAG, L2))


def test_kapi_ihlali_onceki_sevkiyati_bozmaz():
    """Ikinci kosu ihlal ederse dist'te DURAN sevkiyat aynen kalmalidir."""
    _seed()
    materialize.run(TAG, L2, L1)
    before = {name: snapshot.file_digest(_dist(name))
              for name in schema.filenames(L2, L1)}

    store = lexicon_schema.open_lexicon_db()
    with store:
        store.execute("UPDATE sense_examples SET source = 'legacy_dist'")
    store.close()

    with pytest.raises(gate.ShipGateError):
        materialize.run(TAG, L2, L1)
    after = {name: snapshot.file_digest(_dist(name))
             for name in schema.filenames(L2, L1)}
    assert after == before
    assert not os.path.exists(
        os.path.join(paths.dist_dir(TAG, L2), materialize.STAGING))


# --- Uretim -------------------------------------------------------------

def test_uc_dosya_uretilir_ve_icerikleri_ortusur():
    _seed()
    result = materialize.run(TAG, L2, L1)
    assert result.filenames == ["core.db", "en.db", "i18n_tr.db"]

    core = sqlite3.connect(_dist("core.db"))
    text = sqlite3.connect(_dist("en.db"))
    i18n = sqlite3.connect(_dist("i18n_tr.db"))
    try:
        assert core.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 2
        row = text.execute("SELECT headword, gloss, ipa, examples_json FROM"
                           " item_text WHERE item_id = 1").fetchone()
        assert row[0] == "run" and row[1] == "tanim: run" and row[2] == "/run/"
        assert json.loads(row[3]) == ["run ornek 1.", "run ornek 2."]
        assert i18n.execute("SELECT gloss FROM item_gloss WHERE item_id = 1"
                            ).fetchone()[0] == "run-tr"
    finally:
        core.close()
        text.close()
        i18n.close()


def test_l1_verilmezse_i18n_dosyasi_uretilmez():
    _seed()
    result = materialize.run(TAG, L2, None)
    assert result.filenames == ["core.db", "en.db"]
    assert not os.path.exists(_dist("i18n_tr.db"))


def test_lisans_atifi_verinin_yaninda_gider():
    _seed()
    materialize.run(TAG, L2, L1)
    conn = sqlite3.connect(_dist("core.db"))
    value = conn.execute(
        "SELECT value FROM meta WHERE key = 'shippable_sources'").fetchone()[0]
    conn.close()
    names = [s["name"] for s in json.loads(value)]
    assert "ipa_dict" in names and "legacy_dist" not in names


def test_ayni_girdi_ayni_baytlari_uretir():
    """Determinizm: sevkiyat dosyalari zaman damgasi TASIMAZ."""
    _seed()
    materialize.run(TAG, L2, L1)
    first = {n: snapshot.file_digest(_dist(n)) for n in schema.filenames(L2, L1)}
    materialize.run(TAG, L2, L1)
    second = {n: snapshot.file_digest(_dist(n)) for n in schema.filenames(L2, L1)}
    assert second == first


# --- Dogrulama ----------------------------------------------------------

def test_verify_saglam_sevkiyatta_yesildir():
    _seed()
    materialize.run(TAG, L2, L1)
    results = verify.run_checks(TAG, L2, L1)
    assert results and all(r.ok for r in results), \
        "\n".join(str(r) for r in results if not r.ok)


def test_verify_degistirilmis_dosyayi_yakalar():
    """Dist'teki bayt degisirse ozetle uyusmaz — sessizce gecemez."""
    _seed()
    materialize.run(TAG, L2, L1)
    conn = sqlite3.connect(_dist("en.db"))
    with conn:
        conn.execute("UPDATE item_text SET gloss = 'elle degistirildi'")
    conn.close()

    failed = [r for r in verify.run_checks(TAG, L2, L1) if not r.ok]
    assert [r.name for r in failed] == ["en.db ozetle ayni (sha256)"]


def test_verify_sevkiyat_yoksa_duser():
    _seed()
    failed = [r for r in verify.run_checks(TAG, L2, L1) if not r.ok]
    assert failed and any("core.db" in r.name for r in failed)
