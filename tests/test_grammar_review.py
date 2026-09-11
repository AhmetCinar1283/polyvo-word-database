"""
`review`nin grammar alanlarini (`grammar`/`grammar_l1`) duzeltme yolu.

Asil olculen sey: grammar KENDI dosyasinda durur (`data/stores/
grammar.sqlite`), buna ragmen "sorunlu tek satirda hicbir satir yazilmaz"
sozu UC dosya (lexicon/cloze/grammar) arasinda da gecerli kalir; insanin
yazdigi `rule_id` KATALOG KAPISINDAN gecer; `trigger`in cumlede gecmesi
insan yolunda da GEVSETILMEZ (Is 6'nin en guclu kapisi).
"""

from __future__ import annotations

import json
import os

import pytest

from polyvo.core import paths
from polyvo.core.jobs.store import policy
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.cloze import schema as cloze_schema
from polyvo.modules.grammar import schema as grammar_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.review import apply as apply_mod
from polyvo.review import export, record

L1 = "tr"
STABLE_KEY = "en:run:verb"

#: `test_review.py::CLOZE_QUESTIONS`nin triggerlariyla UYUMLU (`keep`,
#: `walked`, `to pay`, `went`, `to ask` cumlede GERCEKTEN geciyor).
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

GRAMMAR_PACKAGE = [
    {"rules": [
        {"rank": 1, "rule_id": "EN.TENSE.PRESENT_SIMPLE", "trigger": "keep",
         "note": "Describes a habitual action."},
    ]},
    {"rules": [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action this morning."},
        {"rank": 2, "rule_id": "EN.INF.TO_INFINITIVE", "trigger": "to pay",
         "note": "Expresses the purpose of the walk."},
    ]},
    {"rules": [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "went",
         "note": "A completed action after the meeting."},
        {"rank": 2, "rule_id": "EN.INF.TO_INFINITIVE", "trigger": "to ask",
         "note": "Expresses the purpose of going to the bank."},
    ]},
]


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _seed_card(sense_id=1001, stable_key=STABLE_KEY):
    """Kimlik + `sense_cards` satirini kurar (grammar'in ATLAMA noktasi)."""
    identity = curriculum_schema.open_identity_db()
    with identity:
        identity.execute(
            "INSERT INTO items (item_id, l2, headword, pos, stable_key)"
            " VALUES (1,'en','run','verb',?)", (stable_key,))
    identity.close()

    lex = lexicon_schema.open_lexicon_db()
    with lex:
        lex.execute(
            "INSERT INTO sense_cards (sense_id, item_id, stable_key,"
            " gloss_en, register, tier, status, reject_reason, source, model,"
            " prompt_hash, updated_at)"
            " VALUES (?,1,?,'tanim: run',NULL,3,'approved',NULL,'model','m',"
            "'h','t')", (sense_id, stable_key))
    lex.close()


def _seed_cloze(sense_id=1001, stable_key=STABLE_KEY):
    """Onayli bir cloze paketi — grammar'in `trigger` dogrulamasinin
    okudugu cumle metni budur."""
    conn = cloze_schema.open_cloze_db()
    with conn:
        conn.execute(
            "INSERT INTO sense_cloze (sense_id, stable_key, status,"
            " reject_reason, warnings, tier, source, model, prompt_hash,"
            " updated_at) VALUES (?,?,'approved',NULL,NULL,3,'model','m',"
            "'h','t')", (sense_id, stable_key))
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


def _seed_grammar(stable_key=STABLE_KEY, package=None, status="approved"):
    """Grammar deposuna bir MODEL paketi yazar — roundtrip'in baslangici."""
    package = package if package is not None else GRAMMAR_PACKAGE
    conn = grammar_schema.open_grammar_db()
    with conn:
        conn.execute(
            "INSERT INTO sentence_grammar (owner, group_key, status,"
            " reject_reason, warnings, tier, source, model, prompt_hash,"
            " source_sha256, updated_at)"
            " VALUES ('cloze',?,?,NULL,NULL,3,'model','m','h','s','t')",
            (stable_key, status))
        for seq, item in enumerate(package, start=1):
            ref = f"{stable_key}:{seq}"
            for rule in item["rules"]:
                conn.execute(
                    "INSERT INTO sentence_grammar_rule (owner, group_key,"
                    " ref, rank, rule_id, trigger, note, tier, source)"
                    " VALUES ('cloze',?,?,?,?,?,?,3,'model')",
                    (stable_key, ref, rule["rank"], rule["rule_id"],
                     rule["trigger"], rule["note"]))
    conn.close()


def _grammar_rows(stable_key=STABLE_KEY):
    """Paket satiri + kural satirlari."""
    conn = grammar_schema.open_grammar_db()
    try:
        package = conn.execute(
            "SELECT status, tier, source, model FROM sentence_grammar"
            " WHERE owner = 'cloze' AND group_key = ?", (stable_key,)).fetchone()
        rules = [tuple(r) for r in conn.execute(
            "SELECT ref, rank, rule_id, trigger, note, tier, source"
            " FROM sentence_grammar_rule WHERE owner = 'cloze'"
            " AND group_key = ? ORDER BY ref, rank", (stable_key,))]
    finally:
        conn.close()
    return (tuple(package) if package else None), rules


def _write_file(tmp_path, rows) -> str:
    """Duzeltme dosyasini JSONL olarak yazar."""
    path = os.path.join(str(tmp_path), "duzeltme.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _seed_ready():
    """Kart + onayli cloze + onayli grammar — grammar duzeltmesinin girdisi."""
    _seed_card()
    _seed_cloze()
    _seed_grammar()


# --- Cikarma -----------------------------------------------------------------

def test_export_grammar_paketini_cikarir():
    """Cikan satirda uc cumle (1+2+2 kural) bulunur."""
    _seed_ready()
    row = next(r for r in export.rows(L1) if r["stable_key"] == STABLE_KEY)
    assert len(row["grammar"]) == 3
    assert [len(item["rules"]) for item in row["grammar"]] == [1, 2, 2]
    assert row["grammar"][0]["rules"][0]["rule_id"] == "EN.TENSE.PRESENT_SIMPLE"


def test_export_grammar_olmayan_karti_bos_alanla_kirletmez():
    """Icerigi olmayan alan hic yazilmaz."""
    _seed_card()
    _seed_cloze()
    row = next(r for r in export.rows(L1) if r["stable_key"] == STABLE_KEY)
    assert "grammar" not in row


def test_grammar_export_ciktisi_dogrudan_geri_okunabilir(tmp_path):
    """Cikardigimiz sey ice aktarilabilir olmali — yoksa duzeltme yolu kirik."""
    _seed_ready()
    row = next(r for r in export.rows(L1) if r["stable_key"] == STABLE_KEY)
    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY,
                                   "grammar": row["grammar"]}])
    corrections, errors = record.parse_file(path)
    assert errors == []
    assert apply_mod.apply(corrections, l1=L1).applied == 1


# --- Ice aktarma: grammar -----------------------------------------------------

def test_import_grammar_insan_satirina_donusturur(tmp_path):
    """Kabul olcutu: `review` grammar'i da duzeltebiliyor — tier 0 / human."""
    _seed_ready()
    duzeltilmis = json.loads(json.dumps(GRAMMAR_PACKAGE))
    duzeltilmis[0]["rules"][0]["note"] = "Duzeltilmis not."

    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY,
                                   "grammar": duzeltilmis}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert result.applied == 1

    package, rules = _grammar_rows()
    assert package[:3] == ("approved", policy.TIER_HUMAN, "human")
    assert rules[0][4] == "Duzeltilmis not."
    assert all(row[5:] == (policy.TIER_HUMAN, "human") for row in rules)


def test_import_grammar_bilinmeyen_rule_id_katalogda_yok_reddedilir(tmp_path):
    """Bicim GECERLI ama katalogda OLMAYAN bir `rule_id` REDDEDILIR — bicim
    kapisi `record.py`de gecer, varlik kapisi `apply.py`de duser."""
    _seed_ready()
    bozuk = json.loads(json.dumps(GRAMMAR_PACKAGE))
    bozuk[0]["rules"][0]["rule_id"] = "EN.MODAL.HICBIR_YERDE_YOK"

    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY, "grammar": bozuk}])
    corrections, errors = record.parse_file(path)
    assert errors == []                        # bicim GECERLI (record.py)
    with pytest.raises(apply_mod.ReviewError) as exc:
        apply_mod.apply(corrections, l1=L1)
    assert "grammar_rule_id_katalogda_yok" in str(exc.value)


def test_import_grammar_rule_id_bicimi_gecersiz_satiri_dusurur(tmp_path):
    """Bicim BILE gecersiz bir `rule_id` (bilinmeyen ALAN) satiri DUSURUR
    — bu kapi `record.py`dedir, dosya okunurken duser."""
    bozuk = json.loads(json.dumps(GRAMMAR_PACKAGE))
    bozuk[0]["rules"][0]["rule_id"] = "EN.NOPE.NOPE"
    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY, "grammar": bozuk}])
    _corrections, errors = record.parse_file(path)
    assert errors and "grammar_rule_id_bicimi_gecersiz" in errors[0]


def test_import_grammar_trigger_cumlede_yok_reddedilir(tmp_path):
    """Kabul olcutu: `trigger` cumlede GECMIYORSA reddedilir — insan yolu
    da AYNI kapiyi gecer (Is 6'nin en guclu olculebilir kapisi)."""
    _seed_ready()
    bozuk = json.loads(json.dumps(GRAMMAR_PACKAGE))
    bozuk[0]["rules"][0]["trigger"] = "hicbir zaman"

    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY, "grammar": bozuk}])
    with pytest.raises(apply_mod.ReviewError) as exc:
        apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert "grammar_trigger_cumlede_yok" in str(exc.value)


def test_bozuk_grammar_satirinda_HICBIR_satir_yazilmaz(tmp_path):
    """UC AYRI SQLITE DOSYASINA (lexicon/cloze/grammar) ragmen atomiklik
    korunur (ATTACH DATABASE)."""
    _seed_ready()
    before_package, before_rules = _grammar_rows()

    bozuk = json.loads(json.dumps(GRAMMAR_PACKAGE))
    bozuk[0]["rules"][0]["trigger"] = "hicbir zaman"
    path = _write_file(tmp_path, [
        {"stable_key": STABLE_KEY, "grammar": bozuk},
        {"stable_key": "en:YOK:noun", "gloss_en": "depoda olmayan anahtar"},
    ])
    with pytest.raises(apply_mod.ReviewError):
        apply_mod.apply(record.parse_file(path)[0], l1=L1)

    after_package, after_rules = _grammar_rows()
    assert after_package == before_package
    assert after_rules == before_rules


def test_grammar_duzeltmesi_data_human_yedegine_dusuyor(tmp_path):
    """Insan emegi depo gitse de geri gelebilmeli."""
    _seed_ready()
    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY,
                                   "grammar": GRAMMAR_PACKAGE}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    saved = json.loads(open(result.backup_path, encoding="utf-8").read().strip())
    assert saved["stable_key"] == STABLE_KEY
    assert len(saved["grammar"]) == 3


# --- Cikarma + ice aktarma: grammar_l1 ---------------------------------------

def _seed_grammar_l1(l1=L1):
    """Grammar not cevirisine bir MODEL satiri ekler."""
    conn = grammar_schema.open_grammar_db()
    with conn:
        conn.execute(
            "INSERT INTO sentence_grammar_translation (owner, group_key, l1,"
            " status, reject_reason, warnings, tier, source, model,"
            " prompt_hash, note_sha256, updated_at)"
            " VALUES ('cloze',?,?,'approved',NULL,NULL,3,'model','m','h',"
            "'n','t')", (STABLE_KEY, l1))
        for seq, item in enumerate(GRAMMAR_PACKAGE, start=1):
            ref = f"{STABLE_KEY}:{seq}"
            for rule in item["rules"]:
                conn.execute(
                    "INSERT INTO sentence_grammar_rule_l1 (owner, ref, rank,"
                    " l1, note, tier, source) VALUES ('cloze',?,?,?,?,3,"
                    "'model')", (ref, rule["rank"], l1, f"TR: {rule['note']}"))
    conn.close()


def test_export_grammar_l1_ceviriyi_cikarir():
    """`--l1` verildiginde `grammar_l1` da cikar — `rule_id`/`trigger` YOK."""
    _seed_ready()
    _seed_grammar_l1()
    row = next(r for r in export.rows(L1) if r["stable_key"] == STABLE_KEY)
    assert len(row["grammar_l1"]) == 3
    assert [len(item["rules"]) for item in row["grammar_l1"]] == [1, 2, 2]
    first_rule = row["grammar_l1"][0]["rules"][0]
    assert set(first_rule) == {"rank", "note"}


def test_import_grammar_l1_insan_satirina_donusturur(tmp_path):
    """Kabul olcutu: grammar not cevirisi de duzeltilebiliyor — tier 0."""
    _seed_ready()
    _seed_grammar_l1()
    row = next(r for r in export.rows(L1) if r["stable_key"] == STABLE_KEY)
    duzeltilmis = json.loads(json.dumps(row["grammar_l1"]))
    duzeltilmis[0]["rules"][0]["note"] = "Elle duzeltilmis Turkce not."

    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY, "l1": L1,
                                   "grammar_l1": duzeltilmis}])
    result = apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert result.applied == 1

    conn = grammar_schema.open_grammar_db()
    note, tier, source = conn.execute(
        "SELECT note, tier, source FROM sentence_grammar_rule_l1"
        " WHERE ref = ? AND rank = 1 AND l1 = ?",
        (f"{STABLE_KEY}:1", L1)).fetchone()
    conn.close()
    assert note == "Elle duzeltilmis Turkce not."
    assert (tier, source) == (policy.TIER_HUMAN, "human")


def test_import_grammar_l1_rank_ingilizce_ile_uyusmuyorsa_reddedilir(tmp_path):
    """Adreslenen `rank` Ingilizce paketteki kural sayisini ASARSA reddedilir
    — cevirinin adresledigi kural GERCEKTEN var olmali."""
    _seed_ready()
    _seed_grammar_l1()
    bozuk = [{"rules": [{"rank": 1, "note": "gecerli not"}]},
             {"rules": [{"rank": 1, "note": "gecerli not"},
                        {"rank": 2, "note": "gecerli not"}]},
             {"rules": [{"rank": 1, "note": "gecerli not"},
                        {"rank": 5, "note": "olmayan ranka not"}]}]
    path = _write_file(tmp_path, [{"stable_key": STABLE_KEY, "l1": L1,
                                   "grammar_l1": bozuk}])
    with pytest.raises(apply_mod.ReviewError) as exc:
        apply_mod.apply(record.parse_file(path)[0], l1=L1)
    assert "grammar_l1_rank_ingilizce_kuralla_uyusmuyor" in str(exc.value)
