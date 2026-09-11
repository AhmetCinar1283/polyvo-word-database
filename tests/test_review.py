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
    """`usage_note` Is 3'ten beri `sense_usage_note`u adresler (kart sutununu
    DEGIL) — `null` orada da GECERLI bir bosaltmadir (bos not = sebep yok)."""
    _seed()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "register": None, "usage_note": None}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)
    card = _card("en:run:verb")
    assert card["register"] is None

    conn = lexicon_schema.open_lexicon_db()
    note_row = conn.execute(
        "SELECT note, status, tier, source FROM sense_usage_note"
        " WHERE sense_id = 1001").fetchone()
    conn.close()
    assert note_row["note"] == "" and note_row["status"] == "approved"
    assert note_row["tier"] == policy.TIER_HUMAN and note_row["source"] == "human"

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


# --- Yeni L1 (es) gidis-donus (Is 2) --------------------------------------

def test_yeni_l1_es_export_import_gidis_donusu(tmp_path):
    """`review export/import --l1 es` kod degisikligi gerektirmeden calisir:
    export.rows(l1) ve apply() zaten `l1` parametreli, `sense_gloss_l1`in
    dogal anahtari `(sense_id, l1)`."""
    _seed()
    rows = export.rows("es")
    # `es` icin henuz karsilik yok — alan hic yazilmaz ("dokunma" degil,
    # "olusturma" bekleniyor: `gloss_l1` anahtari export ciktisinda YOK).
    assert "gloss_l1" not in rows[0]

    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "gloss_l1": "correr", "l1": "es"}])
    result = apply_mod.apply(record.parse_file(path)[0], l1="es")
    assert result.applied == 1

    assert _rows("sense_gloss_l1", 1001) == [
        ("es", "correr", 0, "human"), ("tr", "run-tr", policy.TIER_MODEL, "llm")]
    assert result.backup_path == backup.backup_path()


def test_yeni_l1_es_panel_tum_dilleri_listeler():
    """Panelin kart ayrintisi `sense_gloss_l1`i TUM diller icin sorguluyor
    (kod degisikligi gerekmiyor) — yeni dil eklenince kendiliginden gorunur."""
    from polyvo.modules.lexicon_card.panel import queries

    _seed()
    store = lexicon_schema.open_lexicon_db()
    with store:
        store.execute(
            "INSERT INTO sense_gloss_l1 (sense_id, l1, gloss, tier, source,"
            " model) VALUES (1001, 'es', 'correr', ?, 'llm', 'm')",
            (policy.TIER_MODEL,))
    store.close()

    detail = queries.card("en:run:verb")
    langs = {l1 for l1, _gloss, _tier, _source in detail["glosses_l1"]}
    assert langs == {"tr", "es"}


# --- Is 3: ceviri/not alanlarinin export/import yolu -----------------------

def _seed_translation(sense_id=1001, l1="de", status="approved"):
    """`sense_translation`(+`_examples`) ve `sense_gloss_l1_note`e bir
    model satiri yazar — export/import roundtrip'i icin baslangic durumu."""
    store = lexicon_schema.open_lexicon_db()
    with store:
        store.execute(
            "INSERT INTO sense_translation (sense_id, l1, definition,"
            " usage_note, status, tier, source, model) VALUES"
            " (?,?,?,?,?,?,'llm','m')",
            (sense_id, l1, "schnell zu Fuß bewegen" if status == "approved" else None,
             "" if status == "approved" else None, status, policy.TIER_MODEL))
        if status == "approved":
            store.executemany(
                "INSERT INTO sense_translation_examples (sense_id, l1, seq, text,"
                " tier, source) VALUES (?,?,?,?,?,'llm')",
                [(sense_id, l1, 1, "Ich laufe jeden Morgen.", policy.TIER_MODEL),
                 (sense_id, l1, 2, "Sie liefen über das Feld.", policy.TIER_MODEL)])
        store.execute(
            "INSERT INTO sense_gloss_l1_note (sense_id, l1, note, tier,"
            " source, model) VALUES (?,?,?,?,'llm','m')",
            (sense_id, l1, "borrowed word, no clean equivalent", policy.TIER_MODEL))
    store.close()


def test_export_l1_de_ceviri_ve_gloss_notunu_cikarir():
    _seed()
    _seed_translation()
    rows = export.rows("de")
    row = next(r for r in rows if r["headword"] == "run")
    assert row["definition_l1"] == "schnell zu Fuß bewegen"
    assert row["examples_l1"] == ["Ich laufe jeden Morgen.", "Sie liefen über das Feld."]
    assert row["gloss_note_l1"] == "borrowed word, no clean equivalent"
    # Bos ceviri notu (usage_note_l1) doluymus gibi YAZILMAZ.
    assert "usage_note_l1" not in row


def test_export_reddedilen_ceviri_icerik_cikarmaz():
    """Madde 7: paket reddedilirse ICERIK depoda yoktur, export de bosluk
    birakir — 'dokunma' anlamina gelen davranis burada da gecerli."""
    _seed()
    _seed_translation(status="rejected")
    rows = export.rows("de")
    row = next(r for r in rows if r["headword"] == "run")
    assert "definition_l1" not in row and "examples_l1" not in row


def test_import_l1_de_ceviri_alanlarini_insan_satirina_donusturur(tmp_path):
    _seed()
    _seed_translation()
    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "definition_l1": "sich schnell bewegen",
        "usage_note_l1": "Auch für Geschäftsführung verwendet.",
        "examples_l1": ["Ich laufe.", "Wir laufen."],
        "gloss_note_l1": "aktualisiert"}])
    result = apply_mod.apply(record.parse_file(path)[0], l1="de")
    assert result.applied == 1

    conn = lexicon_schema.open_lexicon_db()
    translation = conn.execute(
        "SELECT definition, usage_note, status, tier, source FROM"
        " sense_translation WHERE sense_id = 1001 AND l1 = 'de'").fetchone()
    examples = [r[0] for r in conn.execute(
        "SELECT text FROM sense_translation_examples WHERE sense_id = 1001"
        " AND l1 = 'de' ORDER BY seq")]
    gloss_note = conn.execute(
        "SELECT note, tier, source FROM sense_gloss_l1_note"
        " WHERE sense_id = 1001 AND l1 = 'de'").fetchone()
    conn.close()

    assert translation["definition"] == "sich schnell bewegen"
    assert translation["usage_note"] == "Auch für Geschäftsführung verwendet."
    assert translation["status"] == "approved"
    assert translation["tier"] == policy.TIER_HUMAN and translation["source"] == "human"
    assert examples == ["Ich laufe.", "Wir laufen."]
    assert gloss_note["note"] == "aktualisiert"
    assert gloss_note["tier"] == policy.TIER_HUMAN and gloss_note["source"] == "human"


def test_import_definition_l1_dokununca_usage_note_l1_korunur(tmp_path):
    """SATIR ICI 'bulunmayan alan dokunulmaz': yalnizca `definition_l1`
    duzeltilince o satirin `usage_note` sutunu (Almanca) degismeden kalir."""
    _seed()
    _seed_translation()
    store = lexicon_schema.open_lexicon_db()
    with store:
        store.execute(
            "UPDATE sense_translation SET usage_note = ? WHERE sense_id = 1001"
            " AND l1 = 'de'", ("mevcut ceviri notu",))
    store.close()

    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "definition_l1": "yeni tanim"}])
    apply_mod.apply(record.parse_file(path)[0], l1="de")

    conn = lexicon_schema.open_lexicon_db()
    row = conn.execute(
        "SELECT definition, usage_note FROM sense_translation"
        " WHERE sense_id = 1001 AND l1 = 'de'").fetchone()
    conn.close()
    assert row["definition"] == "yeni tanim"
    assert row["usage_note"] == "mevcut ceviri notu"


def test_gloss_note_l1_null_ile_bosaltilabilir(tmp_path):
    _seed()
    _seed_translation()
    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "gloss_note_l1": None}])
    apply_mod.apply(record.parse_file(path)[0], l1="de")

    conn = lexicon_schema.open_lexicon_db()
    row = conn.execute(
        "SELECT note FROM sense_gloss_l1_note"
        " WHERE sense_id = 1001 AND l1 = 'de'").fetchone()
    conn.close()
    assert row is None


def test_ceviri_alani_icin_l1_verilmezse_reddedilir(tmp_path):
    _seed()
    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "definition_l1": "tanim"}])
    with pytest.raises(apply_mod.ReviewError, match="l1_verilmedi"):
        apply_mod.apply(record.parse_file(path)[0], l1=None)


def test_ceviri_disi_alan_l1_gerektirmez(tmp_path):
    """`gloss_en` gibi Ingilizce alanlar icin `l1` GEREKMEZ — yalnizca
    per-l1 alanlar bunu ister."""
    _seed()
    path = _write_file(tmp_path, [{
        "stable_key": "en:run:verb", "gloss_en": "yeni tanim"}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=None)
    assert result.applied == 1


# --- Is 4: cloze alanlarinin export/import yolu -----------------------------
# Asil olculen sey: cloze AYRI BIR SQLITE DOSYASINDA durur, buna ragmen
# "sorunlu tek satir varsa hicbir satir yazilmaz" sozu iki dosyada da gecerli
# kalir (`apply.py` ATTACH DATABASE kullanir).

CLOZE_QUESTIONS = [
    {"difficulty": "kolay", "sentence": "I keep my money in a bank.",
     "answer": "bank", "options": ["bank", "spoon", "cloud", "chair"]},
    {"difficulty": "orta",
     "sentence": "She walked to the bank to pay the bill this morning.",
     "answer": "bank", "options": ["bank", "garden", "kitchen", "forest"]},
    {"difficulty": "zor",
     "sentence": "After the long meeting he went to the bank to ask about "
                 "the new office rules and forms.",
     "answer": "bank", "options": ["bank", "office", "garden", "market"]},
]


def _seed_cloze(sense_id=1001, status="approved"):
    """Cloze deposuna bir MODEL paketi yazar — roundtrip'in baslangic durumu."""
    from polyvo.modules.cloze import schema as cloze_schema

    conn = cloze_schema.open_cloze_db()
    with conn:
        conn.execute(
            "INSERT INTO sense_cloze (sense_id, stable_key, status,"
            " reject_reason, warnings, tier, source, model, prompt_hash,"
            " updated_at) VALUES (?,?,?,NULL,NULL,3,'model','m','h','t')",
            (sense_id, "en:run:verb", status))
        for seq, question in enumerate(CLOZE_QUESTIONS, start=1):
            conn.execute(
                "INSERT INTO sense_cloze_question (sense_id, seq, difficulty,"
                " sentence, answer, tier, source) VALUES (?,?,?,?,?,3,'model')",
                (sense_id, seq, question["difficulty"], question["sentence"],
                 question["answer"]))
            for opt_seq, text in enumerate(question["options"], start=1):
                conn.execute(
                    "INSERT INTO sense_cloze_option (sense_id, seq, opt_seq,"
                    " text, is_answer) VALUES (?,?,?,?,?)",
                    (sense_id, seq, opt_seq, text,
                     1 if text == question["answer"] else 0))
    conn.close()


def _cloze_rows(sense_id=1001):
    """Paket satiri + sorular + siklar."""
    from polyvo.modules.cloze import schema as cloze_schema

    conn = cloze_schema.open_cloze_db()
    try:
        package = conn.execute(
            "SELECT status, tier, source, model FROM sense_cloze"
            " WHERE sense_id = ?", (sense_id,)).fetchone()
        questions = [tuple(r) for r in conn.execute(
            "SELECT seq, difficulty, sentence, answer, tier, source FROM"
            " sense_cloze_question WHERE sense_id = ? ORDER BY seq",
            (sense_id,))]
        options = [tuple(r) for r in conn.execute(
            "SELECT seq, opt_seq, text, is_answer FROM sense_cloze_option"
            " WHERE sense_id = ? ORDER BY seq, opt_seq", (sense_id,))]
    finally:
        conn.close()
    return (tuple(package) if package else None), questions, options


def test_export_cloze_paketini_cikarir():
    """Cikan satirda 3 soru, her birinde 4 sik ve dogru cevap bulunur."""
    _seed()
    _seed_cloze()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert len(row["cloze"]) == 3
    assert [q["sentence"] for q in row["cloze"]] ==         [q["sentence"] for q in CLOZE_QUESTIONS]
    assert all(len(q["options"]) == 4 for q in row["cloze"])
    assert row["cloze"][0]["answer"] == "bank"


def test_export_zorluk_etiketini_YAZMAZ():
    """Zorlugu SIRA belirler; dosyaya yazmak duzenlenebilir gibi gosterirdi
    — oysa `apply.py` onu dosyadan hic okumaz."""
    _seed()
    _seed_cloze()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert all("difficulty" not in q for q in row["cloze"])


def test_cloze_export_ciktisi_dogrudan_geri_okunabilir(tmp_path):
    """Cikardigimiz sey ice aktarilabilir olmali — yoksa duzeltme yolu kirik."""
    _seed()
    _seed_cloze()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    path = _write_file(tmp_path, [{"stable_key": row["stable_key"],
                                   "cloze": row["cloze"]}])
    corrections, errors = record.parse_file(path)
    assert errors == []
    assert apply_mod.apply(corrections, l1=L1).applied == 1


def test_export_cloze_olmayan_karti_bos_alanla_kirletmez():
    """Icerigi olmayan alan hic yazilmaz (mevcut kural cloze'da da gecerli)."""
    _seed()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert "cloze" not in row


def test_import_cloze_insan_satirina_donusturur(tmp_path):
    """Kabul olcutu: `review` cloze'u da duzeltebiliyor — tier 0 / human."""
    _seed()
    _seed_cloze()
    duzeltilmis = json.loads(json.dumps(CLOZE_QUESTIONS))
    duzeltilmis[0]["sentence"] = "I put my money in a bank."
    duzeltilmis[0]["options"] = ["bank", "spoon", "cloud", "table"]

    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze": duzeltilmis}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert result.applied == 1

    package, questions, options = _cloze_rows()
    assert package == ("approved", policy.TIER_HUMAN, "human", None)
    assert questions[0][2] == "I put my money in a bank."
    assert all(row[4:] == (policy.TIER_HUMAN, "human") for row in questions)
    assert ("table", 0) in [(text, is_answer) for _s, _o, text, is_answer
                            in options]


def test_import_cloze_zorluk_dosyadan_OKUNMAZ():
    """Zorluk etiketi `difficulty.band_for(seq)`den turer — dosya kandiramaz."""
    from polyvo.modules.cloze.difficulty import band_for
    assert [band_for(seq).name for seq in (1, 2, 3)] == ["kolay", "orta", "zor"]


def test_import_cloze_zorluk_etiketi_sirayla_yazilir(tmp_path):
    """Dosyada zorluk ters yazilsa bile depoya SIRAYLA yazilir."""
    _seed()
    _seed_cloze()
    ters = json.loads(json.dumps(CLOZE_QUESTIONS))
    for question in ters:
        question["difficulty"] = "zor"

    path = _write_file(tmp_path, [{"stable_key": "en:run:verb", "cloze": ters}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)
    _package, questions, _options = _cloze_rows()
    assert [row[1] for row in questions] == ["kolay", "orta", "zor"]


@pytest.mark.parametrize("bozuk, kalip", [
    (CLOZE_QUESTIONS[:2], "cloze_soru_sayisi_uc_degil"),
    ("metin", "cloze"),
])
def test_bozuk_cloze_satiri_dosyayi_dusurur(tmp_path, bozuk, kalip):
    """Biçim hatasi satiri dusurur — QA ile AYNI sabitler kullanilir."""
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze": bozuk}])
    _corrections, errors = record.parse_file(path)
    assert errors and kalip in errors[0]


def test_bozuk_cloze_satirinda_HICBIR_satir_yazilmaz(tmp_path):
    """Iki AYRI SQLITE DOSYASINA ragmen atomiklik korunur (ATTACH DATABASE)."""
    _seed()
    _seed_cloze()
    before_card = _card("en:run:verb")
    before_cloze = _cloze_rows()

    saglam = json.loads(json.dumps(CLOZE_QUESTIONS))
    saglam[0]["sentence"] = "I put my money in a bank."
    path = _write_file(tmp_path, [
        {"stable_key": "en:run:verb", "cloze": saglam},
        {"stable_key": "en:YOK:noun", "gloss_en": "depoda olmayan anahtar"},
    ])
    with pytest.raises(apply_mod.ReviewError):
        apply_mod.apply(record.parse_file(path)[0], l1=L1)

    assert _card("en:run:verb") == before_card      # kart dosyasi el degmemis
    assert _cloze_rows() == before_cloze            # cloze dosyasi da


def test_cloze_duzeltmesi_data_human_yedegine_dusuyor(tmp_path):
    """Insan emegi depo gitse de geri gelebilmeli."""
    _seed()
    _seed_cloze()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze": CLOZE_QUESTIONS}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)

    saved = json.loads(open(result.backup_path, encoding="utf-8").read().strip())
    assert saved["stable_key"] == "en:run:verb"
    assert len(saved["cloze"]) == 3


# --- Is 5: cloze_rationale alanlarinin export/import yolu -------------------
# Asil olculen sey: rationale cloze'un USTUNE yazar (ayni dosya, ayri
# tablolar), `sense_cloze*` uc tablosuna dokunmadan; ve soru insan
# tarafindan degistirilince eski aciklama BAYAT olur (§12, §17).

RATIONALE_QUESTIONS = [
    {"hint": "Think about where people keep or store their money.",
     "reasons": ["A bank keeps your money safe.",
                "A spoon is for eating, not for storing money.",
                "A cloud is water vapor in the sky, unrelated to money.",
                "A chair is furniture you sit on, not a place for money."]},
    {"hint": "Consider a business that handles bill payments.",
     "reasons": ["A bank lets you pay bills and manage money.",
                "A garden is for growing plants, not paying bills.",
                "A kitchen is for cooking, unrelated to paying a bill.",
                "A forest is full of trees, nothing to do with bills."]},
    {"hint": "Picture where you would ask about account paperwork.",
     "reasons": ["A bank is where you ask about accounts and paperwork.",
                "An office is where people work at desks, not forms.",
                "A garden is for plants, unrelated to paperwork.",
                "A market is for buying and selling, not asking forms."]},
]


def _rationale_question_hash(sense_id=1001):
    """O anki `sense_cloze_question`/`_option`den fingerprint hesaplar."""
    from polyvo.modules.cloze.rationale import fingerprint

    _package, questions, options = _cloze_rows(sense_id)
    by_seq: dict[int, list[str]] = {}
    for seq, _opt_seq, text, _is_answer in options:
        by_seq.setdefault(seq, []).append(text)
    return fingerprint.question_sha256([
        {"seq": row[0], "sentence": row[2], "options": by_seq.get(row[0], [])}
        for row in questions])


def _seed_rationale(sense_id=1001, status="approved", l1=None):
    """Cloze deposuna bir MODEL ipucu/aciklama paketi yazar (+ istege bagli
    ceviri). Kaynak soru O ANDAKI cloze sorusundan hash'lenir — TAZE doner."""
    from polyvo.modules.cloze import schema as cloze_schema

    question_hash = _rationale_question_hash(sense_id)
    conn = cloze_schema.open_cloze_db()
    with conn:
        conn.execute(
            "INSERT INTO sense_cloze_rationale (sense_id, stable_key, status,"
            " reject_reason, warnings, tier, source, model, prompt_hash,"
            " question_sha256, updated_at)"
            " VALUES (?,?,?,NULL,NULL,3,'model','m','h',?,'t')",
            (sense_id, "en:run:verb", status, question_hash))
        for seq, item in enumerate(RATIONALE_QUESTIONS, start=1):
            conn.execute(
                "INSERT INTO sense_cloze_hint (sense_id, seq, hint_seq, hint,"
                " tier, source) VALUES (?,?,1,?,3,'model')",
                (sense_id, seq, item["hint"]))
            for opt_seq, reason in enumerate(item["reasons"], start=1):
                conn.execute(
                    "INSERT INTO sense_cloze_option_reason (sense_id, seq,"
                    " opt_seq, reason, tier, source) VALUES (?,?,?,?,3,'model')",
                    (sense_id, seq, opt_seq, reason))
        if l1:
            from polyvo.modules.cloze.rationale import fingerprint

            hints = [{"seq": i, "hint": item["hint"]}
                    for i, item in enumerate(RATIONALE_QUESTIONS, start=1)]
            reasons = [{"seq": i, "opt_seq": j, "reason": reason}
                      for i, item in enumerate(RATIONALE_QUESTIONS, start=1)
                      for j, reason in enumerate(item["reasons"], start=1)]
            rationale_hash = fingerprint.rationale_sha256(hints, reasons)
            conn.execute(
                "INSERT INTO sense_cloze_rationale_translation (sense_id, l1,"
                " status, reject_reason, warnings, tier, source, model,"
                " prompt_hash, rationale_sha256, updated_at)"
                " VALUES (?,?,?,NULL,NULL,3,'model','m','h',?,'t')",
                (sense_id, l1, status, rationale_hash))
            for seq, item in enumerate(RATIONALE_QUESTIONS, start=1):
                conn.execute(
                    "INSERT INTO sense_cloze_hint_l1 (sense_id, l1, seq,"
                    " hint_seq, hint, tier, source)"
                    " VALUES (?,?,?,1,?,3,'model')",
                    (sense_id, l1, seq, f"[{l1}] {item['hint']}"))
                for opt_seq, reason in enumerate(item["reasons"], start=1):
                    conn.execute(
                        "INSERT INTO sense_cloze_option_reason_l1 (sense_id,"
                        " l1, seq, opt_seq, reason, tier, source)"
                        " VALUES (?,?,?,?,?,3,'model')",
                        (sense_id, l1, seq, opt_seq, f"[{l1}] {reason}"))
    conn.close()


def _rationale_rows(sense_id=1001, l1=None):
    """Paket satiri + ipucu + aciklama (+ istege bagli ceviri satirlari)."""
    from polyvo.modules.cloze import schema as cloze_schema

    conn = cloze_schema.open_cloze_db()
    try:
        package = conn.execute(
            "SELECT status, tier, source, model FROM sense_cloze_rationale"
            " WHERE sense_id = ?", (sense_id,)).fetchone()
        hints = [tuple(r) for r in conn.execute(
            "SELECT seq, hint, tier, source FROM sense_cloze_hint"
            " WHERE sense_id = ? ORDER BY seq", (sense_id,))]
        reasons = [tuple(r) for r in conn.execute(
            "SELECT seq, opt_seq, reason, tier, source FROM"
            " sense_cloze_option_reason WHERE sense_id = ?"
            " ORDER BY seq, opt_seq", (sense_id,))]
        l1_rows = None
        if l1:
            l1_hints = [tuple(r) for r in conn.execute(
                "SELECT seq, hint FROM sense_cloze_hint_l1"
                " WHERE sense_id = ? AND l1 = ? ORDER BY seq", (sense_id, l1))]
            l1_reasons = [tuple(r) for r in conn.execute(
                "SELECT seq, opt_seq, reason FROM sense_cloze_option_reason_l1"
                " WHERE sense_id = ? AND l1 = ? ORDER BY seq, opt_seq",
                (sense_id, l1))]
            l1_rows = (l1_hints, l1_reasons)
    finally:
        conn.close()
    return (tuple(package) if package else None), hints, reasons, l1_rows


def test_export_cloze_rationale_paketini_cikarir():
    """Cikan satirda 3 ipucu + soru basina 4 aciklama bulunur."""
    _seed()
    _seed_cloze()
    _seed_rationale()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert len(row["cloze_rationale"]) == 3
    assert all(len(item["reasons"]) == 4 for item in row["cloze_rationale"])
    assert row["cloze_rationale"][0]["hint"] == RATIONALE_QUESTIONS[0]["hint"]


def test_export_cloze_rationale_l1_paketini_cikarir():
    """`--l1` verilince cevrilmis ipucu/aciklama da cikar."""
    _seed()
    _seed_cloze()
    _seed_rationale(l1=L1)
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert len(row["cloze_rationale_l1"]) == 3
    assert row["cloze_rationale_l1"][0]["hint"].startswith(f"[{L1}]")


def test_export_cloze_rationale_olmayan_karti_bos_alanla_kirletmez():
    """Icerigi olmayan alan hic yazilmaz."""
    _seed()
    _seed_cloze()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    assert "cloze_rationale" not in row
    assert "cloze_rationale_l1" not in row


def test_cloze_rationale_export_ciktisi_dogrudan_geri_okunabilir(tmp_path):
    """Cikardigimiz sey ice aktarilabilir olmali."""
    _seed()
    _seed_cloze()
    _seed_rationale()
    row = next(r for r in export.rows(L1) if r["stable_key"] == "en:run:verb")
    path = _write_file(tmp_path, [{"stable_key": row["stable_key"],
                                   "cloze_rationale": row["cloze_rationale"]}])
    corrections, errors = record.parse_file(path)
    assert errors == []
    assert apply_mod.apply(corrections, l1=L1).applied == 1


def test_import_cloze_rationale_insan_satirina_donusturur(tmp_path):
    """Kabul olcutu: `review` rationale'i de duzeltebiliyor — tier 0 / human."""
    _seed()
    _seed_cloze()
    _seed_rationale()
    duzeltilmis = json.loads(json.dumps(RATIONALE_QUESTIONS))
    duzeltilmis[0]["hint"] = "Think about a place for savings and payments."

    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze_rationale": duzeltilmis}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert result.applied == 1

    package, hints, reasons, _l1 = _rationale_rows()
    assert package[:3] == ("approved", policy.TIER_HUMAN, "human")
    assert hints[0][1] == "Think about a place for savings and payments."
    assert all(row[2:] == (policy.TIER_HUMAN, "human") for row in hints)
    assert all(row[3:] == (policy.TIER_HUMAN, "human") for row in reasons)


def test_import_cloze_rationale_sha_o_anki_sorudan_hesaplanir(tmp_path):
    """`question_sha256` insanin yazdigi satirda da O ANKI cloze sorusundan
    yeniden hesaplanir — insan duzeltmesi BAYAT dogmaz (§17)."""
    _seed()
    _seed_cloze()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze_rationale": RATIONALE_QUESTIONS}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)

    from polyvo.modules.cloze import schema as cloze_schema
    conn = cloze_schema.open_cloze_db()
    stored_hash = conn.execute(
        "SELECT question_sha256 FROM sense_cloze_rationale"
        " WHERE sense_id = 1001").fetchone()[0]
    conn.close()
    assert stored_hash == _rationale_question_hash()


def test_cloze_sorusu_degisince_rationale_bayat_olur(tmp_path):
    """Kabul olcutu (§12): cloze sorusu insan tarafindan DEGISTIRILINCE o
    anlamin rationale'i BAYAT olur ve yeniden islenebilir sayilir."""
    from polyvo.modules.cloze.rationale.store import ClozeRationaleStore
    from polyvo.core.jobs.base import JobContext

    _seed()
    _seed_cloze()
    _seed_rationale()                          # TAZE yazildi (guncel hash)

    store = ClozeRationaleStore()
    assert "en:run:verb" in store.load_existing(JobContext(tag="x", l2="en"))
    store.close()

    duzeltilmis = json.loads(json.dumps(CLOZE_QUESTIONS))
    duzeltilmis[0]["sentence"] = "I put my money in a bank."
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze": duzeltilmis}])
    apply_mod.apply(record.parse_file(path)[0], l1=L1)

    store = ClozeRationaleStore()
    assert "en:run:verb" not in store.load_existing(
        JobContext(tag="x", l2="en"))            # BAYAT: hic donmedi
    store.close()


@pytest.mark.parametrize("bozuk, kalip", [
    (RATIONALE_QUESTIONS[:2], "rationale_soru_sayisi_uc_degil"),
    ("metin", "rationale_soru_sayisi_uc_degil"),
])
def test_bozuk_cloze_rationale_satiri_dosyayi_dusurur(tmp_path, bozuk, kalip):
    """Bicim hatasi satiri dusurur — cloze ile AYNI sozlesme kullanilir."""
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze_rationale": bozuk}])
    _corrections, errors = record.parse_file(path)
    assert errors and kalip in errors[0]


def test_bozuk_cloze_rationale_satirinda_HICBIR_satir_yazilmaz(tmp_path):
    """Iki AYRI SQLITE DOSYASINA ragmen atomiklik korunur (ATTACH DATABASE)."""
    _seed()
    _seed_cloze()
    _seed_rationale()
    before_card = _card("en:run:verb")
    before_rationale = _rationale_rows()

    saglam = json.loads(json.dumps(RATIONALE_QUESTIONS))
    saglam[0]["hint"] = "Think about savings accounts and safekeeping."
    path = _write_file(tmp_path, [
        {"stable_key": "en:run:verb", "cloze_rationale": saglam},
        {"stable_key": "en:YOK:noun", "gloss_en": "depoda olmayan anahtar"},
    ])
    with pytest.raises(apply_mod.ReviewError):
        apply_mod.apply(record.parse_file(path)[0], l1=L1)

    assert _card("en:run:verb") == before_card
    assert _rationale_rows() == before_rationale


def test_cloze_rationale_duzeltmesi_data_human_yedegine_dusuyor(tmp_path):
    """Insan emegi depo gitse de geri gelebilmeli."""
    _seed()
    _seed_cloze()
    _seed_rationale()
    path = _write_file(tmp_path, [{"stable_key": "en:run:verb",
                                   "cloze_rationale": RATIONALE_QUESTIONS}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)

    saved = json.loads(open(result.backup_path, encoding="utf-8").read().strip())
    assert saved["stable_key"] == "en:run:verb"
    assert len(saved["cloze_rationale"]) == 3
