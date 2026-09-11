"""
Grammar panel sayfasi testleri.

Dort soz civilenir:
  1. Sayfa `APP.panel`den gelir: host'ta TEK SATIR degismeden gorunur.
  2. Grammar modulu `polyvo.panel`i IMPORT ETMEZ (yon kurali, AST ile taranir).
  3. Iki gorunum vardir: cumleye gore (`/grammar`) ve kurala gore
     (`/grammar/rules`); adaylar AYRI bir listede (`/grammar/candidates`),
     "sevk edilmez" etiketiyle.
  4. Depodan gelen metin HTML olarak YORUMLANMAZ.

Soket acilmaz: `dispatch` saf bir fonksiyondur, testler onu cagirir.
"""

from __future__ import annotations

import ast
import os

import pytest

from grammar_helpers import (
    FakeProvider,
    grammar_answer,
    run_cloze,
    run_grammar,
    seed_all,
)
from polyvo.core import paths
from polyvo.core.cli import discovery
from polyvo.modules.grammar import schema
from polyvo.modules.grammar.panel import queries
from polyvo.panel import dispatch, pages

GRAMMAR_ROOT = os.path.join("src", "polyvo", "modules", "grammar")


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _serve(path: str):
    """Sayfayi gercek host yolundan (kesif -> mount -> dispatch) cagirir."""
    return dispatch.dispatch(pages.mounted_pages(), path)


def _seed_ready():
    """Onayli bir grammar paketi — panelin gosterecegi girdi."""
    seed_all()
    run_cloze(FakeProvider())
    run_grammar(FakeProvider(answer=grammar_answer()))


# --- 1. Sayfa kesiften gelir -----------------------------------------------

def test_sayfa_host_dosyasi_degismeden_kesiften_gelir():
    """Kabul olcutu: host bir sayfa listesi TUTMAZ; /grammar `APP.panel`den."""
    app = next(a for a in discovery.find_apps(strict=True) if a.name == "grammar")
    assert app.panel is not None and app.panel.prefix == "/grammar"
    assert "/grammar" in [p.prefix for p in pages.mounted_pages()]


def test_liste_sayfasi_bos_depoda_bile_acilir():
    """Hic paket yokken de sayfa 200 doner — panel kurulumu kosuya bagli degil."""
    status, ctype, _body = _serve("/grammar")
    assert (status, ctype.split(";")[0]) == (200, "text/html")
    for extra in ("/grammar/rules", "/grammar/candidates"):
        assert _serve(extra)[0] == 200


def test_bilinmeyen_alt_yol_dort_yuz_dort():
    """Sayfa kendi 404'unu uretir, host'u dusurmez."""
    assert _serve("/grammar/yok")[0] == 404
    assert _serve("/grammar/sentence")[0] == 400        # anahtar verilmedi
    assert _serve("/grammar/sentence?owner=cloze&group_key=en:zzz:noun")[0] == 404
    assert _serve("/grammar/rule")[0] == 400
    assert _serve("/grammar/rule?id=EN.NOPE.NOPE")[0] == 404


# --- 2. Yon kurali ----------------------------------------------------------

def test_grammar_panel_katmanini_import_etmez():
    """Demir kural: modul -> panel importu YUKARI dogrudur, yasaktir."""
    offenders = []
    for dirpath, _dirs, names in os.walk(GRAMMAR_ROOT):
        for name in (n for n in names if n.endswith(".py")):
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                imported = ([a.name for a in node.names]
                            if isinstance(node, ast.Import)
                            else [node.module or ""]
                            if isinstance(node, ast.ImportFrom) else [])
                if any(m == "polyvo.panel" or m.startswith("polyvo.panel.")
                       for m in imported):
                    offenders.append(path)
    assert offenders == []


def test_grammar_panel_hicbir_kardes_modulu_import_etmez():
    """Panel dahil, grammar agacinin HICBIR yerinde `polyvo.modules.cloze`
    (ya da baska bir kardes) import edilmez — cumle metni SEAM'den okunur."""
    offenders = []
    for dirpath, _dirs, names in os.walk(GRAMMAR_ROOT):
        for name in (n for n in names if n.endswith(".py")):
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                imported = ([a.name for a in node.names]
                            if isinstance(node, ast.Import)
                            else [node.module or ""]
                            if isinstance(node, ast.ImportFrom) else [])
                for m in imported:
                    if m.startswith("polyvo.modules.") and not \
                            m.startswith("polyvo.modules.grammar"):
                        offenders.append((path, m))
    assert offenders == []


# --- 3. Iki gorunum + adaylar ------------------------------------------------

def test_cumleye_gore_gorunum_paketi_gosterir():
    """`/grammar/sentence` uc cumlenin ranklanmis kurallarini gosterir."""
    _seed_ready()
    package = queries.sentence_package("cloze", "en:bank:noun")
    assert package["status"] == "approved"
    assert [len(package["rules_by_ref"].get(s["ref"], []))
           for s in package["sentences"]] == [1, 2, 2]

    body = _serve(
        "/grammar/sentence?owner=cloze&group_key=en:bank:noun")[2].decode("utf-8")
    assert "EN.TENSE.PRESENT_SIMPLE" in body
    assert "EN.INF.TO_INFINITIVE" in body


def test_kurala_gore_gorunum_kullanim_sayar():
    """`/grammar/rules` + `/grammar/rule` — bir kuralin KAC cumlede
    kullanildigi ve o cumlelerin listesi."""
    _seed_ready()
    rules = queries.list_rules()
    present = next(r for r in rules if r["rule"].id == "EN.TENSE.PAST_SIMPLE")
    assert present["uses"] == 2                    # seq 2 ve seq 3'te rank 1

    found = queries.rule_usage("EN.TENSE.PAST_SIMPLE")
    assert len(found["usages"]) == 2
    body = _serve("/grammar/rule?id=EN.TENSE.PAST_SIMPLE")[2].decode("utf-8")
    assert "en:bank:noun" in body


def test_adaylar_ayri_listede_sevk_edilmez_etiketiyle():
    """Kabul olcutu: adaylar kurala/cumleye gore gorunumden AYRI, 'sevk
    edilmez' etiketiyle gosterilir — hicbir cumleye kural olarak BAGLANMAZ."""
    _seed_ready()
    conn = schema.open_grammar_db()
    with conn:
        conn.execute(
            "INSERT INTO grammar_candidate (owner, ref, seq, proposed_name,"
            " trigger, rationale, status)"
            " VALUES ('cloze','en:bank:noun:1',1,'Some New Pattern',"
            "'keep money','Gorulen ama katalogda karsiligi olmayan yapi',"
            "'new')")
    conn.close()

    package = queries.sentence_package("cloze", "en:bank:noun")
    assert len(package["candidates_by_ref"].get("en:bank:noun:1", [])) == 1

    body = _serve("/grammar/candidates")[2].decode("utf-8")
    assert "Some New Pattern" in body
    assert "sevk edilmez" in body.lower()

    # Aday, kurala gore gorunumde HIC gecmez (katalogdan bagimsiz).
    rules_body = _serve("/grammar/rules")[2].decode("utf-8")
    assert "Some New Pattern" not in rules_body


# --- 4. Icerik ve kacis -------------------------------------------------------

def test_depodan_gelen_metin_html_olarak_yorumlanmaz():
    """Kabul olcutu: depoda ne yazarsa yazsin panelde ETIKET olmaz."""
    _seed_ready()
    conn = schema.open_grammar_db()
    with conn:
        conn.execute(
            "UPDATE sentence_grammar_rule SET note = ? WHERE rank = 1"
            " AND ref = 'en:bank:noun:1'",
            ("<script>alert(1)</script> not",))
    conn.close()

    body = _serve(
        "/grammar/sentence?owner=cloze&group_key=en:bank:noun")[2].decode("utf-8")
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_bayat_grup_panelde_acikca_gorunur():
    """Kabul olcutu (§17/§18 deseni): seam'deki cumle degisince grup panelde
    acikca BAYAT gorunur, gizlenmez."""
    _seed_ready()
    from cloze_helpers import TAG, L2
    from polyvo.modules.cloze import schema as cloze_schema
    conn = cloze_schema.open_cloze_db()
    with conn:
        conn.execute("UPDATE sense_cloze_question SET sentence = ?"
                     " WHERE seq = 1",
                     ("I put my savings in a bank every month.",))
    conn.close()

    package = queries.sentence_package("cloze", "en:bank:noun")
    assert package["stale"] is True
    body = _serve("/grammar")[2].decode("utf-8")
    assert "BAYAT" in body


def test_panel_hicbir_yazma_sorgusu_icermez():
    """Duzeltme yolu `review`dir: panel katmani depoya YAZMAZ."""
    writes = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE")
    panel_dir = os.path.join(GRAMMAR_ROOT, "panel")
    offenders = []
    for name in sorted(os.listdir(panel_dir)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(panel_dir, name)
        text = open(path, encoding="utf-8").read().upper()
        if any(f" {word} " in text or f'"{word} ' in text for word in writes):
            offenders.append(path)
    assert offenders == []
