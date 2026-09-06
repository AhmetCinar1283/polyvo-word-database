"""
`review` testleri — insan duzeltme yolunun uc sozu olculur:

  1. Ice aktarma `tier=0`/`source="human"`i SABIT yazar; dosyada ne yazarsa
     yazsin okumaz.
  2. Sorunlu tek satir varsa HICBIR SATIR yazilmaz.
  3. Yazilan her duzeltme `data/human/` yedegine gider ve geri oynatilabilir.

Hicbir ag/LLM cagrisi yok: depo elle kurulur.
"""

from __future__ import annotations

import json
import os

import pytest

from polyvo.core import paths
from polyvo.core.jobs.store import policy
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.review import apply as apply_mod
from polyvo.review import backup, export, record

L1 = "tr"

#: (headword, pos, status, gloss_en)
WORDS = [
    ("run", "verb", "approved", "tanim: run"),
    ("apple", "noun", "approved", "tanim: apple"),
    ("gibberish", "noun", "rejected", None),
]


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _seed(words=WORDS):
    """Kimlik + odenmis depoyu testin bekledigi hale getirir."""
    _seed_identity(words)
    _seed_store(words)


def _seed_identity(words=WORDS):
    """Yalnizca kimlik deposunu kurar."""
    identity = curriculum_schema.open_identity_db()
    with identity:
        identity.executemany(
            "INSERT INTO items (item_id, l2, headword, pos, stable_key)"
            " VALUES (?,?,?,?,?)",
            [(i, "en", head, pos, f"en:{head}:{pos}")
             for i, (head, pos, *_rest) in enumerate(words, start=1)])
    identity.close()


def _seed_store(words=WORDS):
    """Yalnizca odenmis depoyu kurar (kimlik ayakta kalir)."""
    store = lexicon_schema.open_lexicon_db()
    with store:
        for i, (head, pos, status, gloss) in enumerate(words, start=1):
            sense_id = 1000 + i
            store.execute(
                "INSERT INTO sense_cards (sense_id, item_id, stable_key,"
                " gloss_en, register, usage_note, tier, status, reject_reason,"
                " source, model) VALUES (?,?,?,?,?,?,?,?,?,'llm','m')",
                (sense_id, i, f"en:{head}:{pos}", gloss, "neutral", "",
                 policy.TIER_MODEL, status,
                 None if status == "approved" else "gloss_en_bos"))
            if status != "approved":
                continue
            store.execute(
                "INSERT INTO sense_gloss_l1 (sense_id, l1, gloss, tier, source,"
                " model) VALUES (?,?,?,?,'llm','m')",
                (sense_id, L1, f"{head}-tr", policy.TIER_MODEL))
            store.executemany(
                "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
                " VALUES (?,?,?,?,'llm')",
                [(sense_id, seq, f"{head} ornek {seq}.", policy.TIER_MODEL)
                 for seq in (1, 2)])
    store.close()


def _card(stable_key: str) -> dict:
    """Depodaki kart satirini sozluk olarak okur."""
    conn = lexicon_schema.open_lexicon_db()
    try:
        row = conn.execute(
            "SELECT sense_id, gloss_en, register, usage_note, tier, status,"
            " reject_reason, source, model FROM sense_cards WHERE stable_key = ?",
            (stable_key,)).fetchone()
    finally:
        conn.close()
    return dict(zip(("sense_id", "gloss_en", "register", "usage_note", "tier",
                     "status", "reject_reason", "source", "model"), row))


def _rows(table: str, sense_id: int) -> list[tuple]:
    """Bir kartin bagli satirlarini doner."""
    columns = {"sense_examples": "seq, text, tier, source",
               "sense_gloss_l1": "l1, gloss, tier, source"}[table]
    conn = lexicon_schema.open_lexicon_db()
    try:
        return [tuple(row) for row in conn.execute(
            f"SELECT {columns} FROM {table} WHERE sense_id = ? ORDER BY 1",
            (sense_id,))]
    finally:
        conn.close()


def _write_file(tmp_path, rows) -> str:
    """Duzeltme dosyasini JSONL olarak yazar."""
    path = os.path.join(str(tmp_path), "duzeltme.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


# --- Cikarma -------------------------------------------------------------

def test_export_satirlari_item_id_sirasinda_cikarir():
    _seed()
    rows = export.rows(L1)
    assert [r["headword"] for r in rows] == ["run", "apple", "gibberish"]
    assert rows[0]["gloss_l1"] == "run-tr"
    assert rows[0]["examples"] == ["run ornek 1.", "run ornek 2."]


def test_export_reddedilen_karti_icerik_alanlari_olmadan_cikarir():
    """Reddedilen kartin icerigi depoda YOKTUR; sebep yine de gorunur."""
    _seed()
    rows = export.rows(L1, status="rejected")
    assert len(rows) == 1
    # Icerigi olmayan alan dosyaya HIC yazilmaz ("dokunma" anlamina gelir).
    assert "gloss_en" not in rows[0] and "examples" not in rows[0]
    assert rows[0]["reject_reason"] == "gloss_en_bos"


def test_export_ciktisi_geri_okunabilir(tmp_path):
    """Cikan dosya, ice aktarmanin ayristiricisindan sorunsuz gecmeli."""
    _seed()
    path = export.write(export.rows(L1), os.path.join(str(tmp_path), "x.jsonl"))
    corrections, problems = record.parse_file(path)
    assert problems == []
    assert len(corrections) == 3


# --- Ice aktarma ---------------------------------------------------------

def test_ice_aktarma_tier_sifir_ve_human_yazar(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_en": "insanin yazdigi tanim"}])
    corrections, _ = record.parse_file(path)
    apply_mod.apply(corrections, l1=L1)

    card = _card("en:run:verb")
    assert card["gloss_en"] == "insanin yazdigi tanim"
    assert card["tier"] == policy.TIER_HUMAN and card["source"] == "human"
    assert card["status"] == "approved" and card["model"] is None


def test_dosyadaki_tier_ve_source_OKUNMAZ(tmp_path):
    """Bir metin dosyasi kendini 'model karari' ilan edip kapiyi kandiramaz."""
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb", "tier": 3,
                                   "source": "llm", "status": "rejected",
                                   "gloss_en": "duzeltilmis"}])
    corrections, problems = record.parse_file(path)
    assert problems == []
    result = apply_mod.apply(corrections, l1=L1)
    assert result.ignored_fields == 3

    card = _card("en:run:verb")
    assert card["tier"] == policy.TIER_HUMAN
    assert card["source"] == "human" and card["status"] == "approved"


def test_bulunmayan_alan_dokunulmaz(tmp_path):
    """Yalnizca gloss duzeltildiginde ornekler oldugu gibi kalir."""
    _seed()
    before = _rows("sense_examples", 1001)
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_en": "yalnizca gloss"}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert _rows("sense_examples", 1001) == before


def test_ornekler_ve_l1_insan_satirina_donusur(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{
        "stable_key": "en:apple:noun", "gloss_l1": "elma",
        "examples": ["Insanin yazdigi ornek."]}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)

    assert _rows("sense_gloss_l1", 1002) == [("tr", "elma", 0, "human")]
    assert _rows("sense_examples", 1002) == [(1, "Insanin yazdigi ornek.", 0, "human")]


def test_null_yalnizca_bosaltilabilir_alanda_gecerli(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "register": None, "usage_note": None}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)
    card = _card("en:run:verb")
    assert card["register"] is None and card["usage_note"] is None

    correction, problem = record.parse_line(
        json.dumps({"stable_key": "en:run:verb", "gloss_en": None}))
    assert correction is None and problem == "gloss_en_bos_birakilamaz"


def test_reddedilen_kart_duzeltilince_onaylanir(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:gibberish:noun",
                                   "gloss_en": "insanin yazdigi tanim",
                                   "examples": ["Bir ornek cumle."]}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    card = _card("en:gibberish:noun")
    assert card["status"] == "approved" and card["reject_reason"] is None
    assert result.still_unapproved == []


def test_yalnizca_ornek_duzeltilirse_kart_reddedilmis_kalir(tmp_path):
    """Ornegi duzeltmek karti onaylamaz — sonuc raporda ACIKCA soylenir."""
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:gibberish:noun",
                                   "examples": ["Bir ornek cumle."]}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert result.still_unapproved == ["en:gibberish:noun"]


# --- Sifir yazma sozu ----------------------------------------------------

def test_bilinmeyen_alan_satiri_dusurur():
    """`gloss_tr` yazim hatasi 'hicbir sey olmadi'yla sonuclanmamali."""
    correction, problem = record.parse_line(
        json.dumps({"stable_key": "en:run:verb", "gloss_tr": "elma"}))
    assert correction is None and problem == "bilinmeyen_alan: gloss_tr"


def test_depoda_olmayan_anahtar_hicbir_satir_yazdirmaz(tmp_path):
    """Kimlik URETILMEZ: bilinmeyen anahtar tum kosuyu durdurur."""
    _seed()
    path = _write_file(tmp_path, [
        {"stable_key": "en:run:verb", "gloss_en": "yazilmamali"},
        {"stable_key": "en:yok:noun", "gloss_en": "karsiligi yok"}])
    with pytest.raises(apply_mod.ReviewError):
        apply_mod.apply(record.parse_file(path)[0], l1=L1)

    assert _card("en:run:verb")["gloss_en"] == "tanim: run"
    assert _card("en:run:verb")["tier"] == policy.TIER_MODEL
    assert not os.path.exists(backup.backup_path())


def test_skip_unknown_ile_kalan_satirlar_yazilir(tmp_path):
    _seed()
    path = _write_file(tmp_path, [
        {"stable_key": "en:run:verb", "gloss_en": "yazilmali"},
        {"stable_key": "en:yok:noun", "gloss_en": "karsiligi yok"}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1,
                             skip_unknown=True)
    assert result.applied == 1 and result.skipped_unknown == 1
    assert _card("en:run:verb")["gloss_en"] == "yazilmali"


def test_l1_verilmezse_gloss_l1_yazilmaz(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_l1": "kosmak"}])
    with pytest.raises(apply_mod.ReviewError):
        apply_mod.apply(record.parse_file(path)[0], l1=None)
    assert _rows("sense_gloss_l1", 1001) == [("tr", "run-tr", 3, "llm")]


# --- Yedek + geri oynatma ------------------------------------------------

def test_yedek_data_human_altina_yazilir(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_en": "insan tanimi"}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)

    assert result.backup_path == backup.backup_path()
    assert os.path.dirname(result.backup_path) == paths.human_dir()
    saved = json.loads(open(result.backup_path, encoding="utf-8").read().strip())
    assert saved["stable_key"] == "en:run:verb"
    assert saved["gloss_en"] == "insan tanimi" and saved["l1"] == L1
    # Yedek tier/source TASIMAZ — o alanlar `apply.py`nin sabitidir.
    assert "tier" not in saved and "source" not in saved


def test_yedek_depo_yeniden_kurulunca_geri_oynatilir(tmp_path):
    """Adim 7'nin asil sozu: depo gitse de insan emegi geri gelir."""
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_en": "insan tanimi",
                                   "gloss_l1": "kosmak"}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)

    os.remove(lexicon_schema.lexicon_db_path())        # depo yok oldu
    _seed_store()                                      # sifirdan kuruldu
    assert _card("en:run:verb")["tier"] == policy.TIER_MODEL

    corrections, problems = backup.read()
    assert problems == []
    result = apply_mod.apply(corrections, l1=None, skip_unknown=True,
                             write_backup=False)
    assert result.applied == 1
    card = _card("en:run:verb")
    assert card["gloss_en"] == "insan tanimi" and card["tier"] == policy.TIER_HUMAN
    # `l1` yedekten ADRES olarak okunur: --l1 verilmese de dogru dile duser.
    assert _rows("sense_gloss_l1", 1001) == [("tr", "kosmak", 0, "human")]


def test_geri_oynatma_yedegi_buyutmez(tmp_path):
    """`restore` yedege TEKRAR yazmaz; yoksa her kosuda ikiye katlanirdi."""
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "gloss_en": "insan tanimi"}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)
    before = open(backup.backup_path(), encoding="utf-8").read()

    corrections, _ = backup.read()
    apply_mod.apply(corrections, l1=L1, skip_unknown=True, write_backup=False)
    assert open(backup.backup_path(), encoding="utf-8").read() == before
