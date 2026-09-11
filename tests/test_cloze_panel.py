"""
Cloze panel sayfasi testleri — mimarinin asil sinavi burada olculur.

Uc soz civilenir:
  1. Sayfa `APP.panel`den gelir: host'ta TEK SATIR degismeden gorunur.
  2. Cloze modulu `polyvo.panel`i IMPORT ETMEZ (yon kurali, AST ile taranir).
  3. Depodan gelen metin HTML olarak YORUMLANMAZ.

Soket acilmaz: `dispatch` saf bir fonksiyondur, testler onu cagirir.
"""

from __future__ import annotations

import ast
import os

import pytest

from cloze_helpers import (
    FakeProvider, rationale_answer, run_cloze, run_rationale, seed_all,
)
from polyvo.core import paths
from polyvo.core.cli import discovery
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.panel import queries
from polyvo.panel import dispatch, pages

CLOZE_ROOT = os.path.join("src", "polyvo", "modules", "cloze")


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _seed_identity(rows=(("bank", "noun"),)):
    """Panelin ad cozmek icin okudugu kimlik deposu."""
    conn = curriculum_schema.open_identity_db()
    with conn:
        conn.executemany(
            "INSERT INTO items (item_id, l2, headword, pos, stable_key)"
            " VALUES (?,?,?,?,?)",
            [(i, "en", head, pos, f"en:{head}:{pos}")
             for i, (head, pos) in enumerate(rows, start=1)])
    conn.close()


def _serve(path: str):
    """Sayfayi gercek host yolundan (kesif -> mount -> dispatch) cagirir."""
    return dispatch.dispatch(pages.mounted_pages(), path)


# --- 1. Sayfa kesiften gelir -----------------------------------------------

def test_sayfa_host_dosyasi_degismeden_kesiften_gelir():
    """Kabul olcutu: host bir sayfa listesi TUTMAZ; /cloze `APP.panel`den."""
    app = next(a for a in discovery.find_apps(strict=True) if a.name == "cloze")
    assert app.panel is not None and app.panel.prefix == "/cloze"
    assert "/cloze" in [p.prefix for p in pages.mounted_pages()]


def test_liste_sayfasi_bos_depoda_bile_acilir():
    """Hic paket yokken de sayfa 200 doner — panel kurulumu koşuya bagli degil."""
    status, ctype, _body = _serve("/cloze")
    assert (status, ctype.split(";")[0]) == (200, "text/html")


def test_bilinmeyen_alt_yol_dort_yuz_dort():
    """Sayfa kendi 404'unu uretir, host'u dusurmez."""
    assert _serve("/cloze/yok")[0] == 404
    assert _serve("/cloze/sense")[0] == 400            # anahtar verilmedi
    assert _serve("/cloze/sense?key=en:zzz:noun")[0] == 404


# --- 2. Yon kurali ----------------------------------------------------------

def test_cloze_panel_katmanini_import_etmez():
    """Demir kural: modul -> panel importu YUKARI dogrudur, yasaktir."""
    offenders = []
    for dirpath, _dirs, names in os.walk(CLOZE_ROOT):
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


# --- 3. Icerik ve kacis -----------------------------------------------------

def test_paket_ayrintisi_uc_soruyu_ve_dogru_cevabi_gosterir():
    """Ayrinti sayfasi 3 soruyu, bosluklu cumleyi ve isaretli cevabi gosterir."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())

    package = queries.package("en:bank:noun")
    assert [q["difficulty"] for q in package["questions"]] == \
        ["kolay", "orta", "zor"]
    assert all("____" in q["blanked"] for q in package["questions"])
    assert all(sum(1 for _t, is_answer in q["options"] if is_answer) == 1
               for q in package["questions"])

    status, _ctype, body = _serve("/cloze/sense?key=en:bank:noun")
    text = body.decode("utf-8")
    assert status == 200
    assert "kolay" in text and "zor" in text and "____" in text


def test_depodan_gelen_metin_html_olarak_yorumlanmaz():
    """Kabul olcutu: depoda ne yazarsa yazsin panelde ETIKET olmaz."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())

    conn = schema.open_cloze_db()
    with conn:
        conn.execute("UPDATE sense_cloze_question SET sentence = ?"
                     " WHERE seq = 1", ("<script>alert(1)</script> bank",))
    conn.close()

    body = _serve("/cloze/sense?key=en:bank:noun")[2].decode("utf-8")
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_tekduzelik_ozeti_qa_ile_ayni_tanimi_sayar():
    """Panelin saydigi acilis kalibi, QA'nin reddettigi kalibin AYNISI."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())

    summary = queries.variety_summary()
    assert summary["sentences"] == 3
    assert summary["distinct_openings"] == 3        # uc farkli acilis
    body = _serve("/cloze")[2].decode("utf-8")
    assert "Tekduzelik" in body


def test_liste_durum_filtresi_calisir():
    """Liste sayfasi duruma gore suzulur — salt okunur, POST yok."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())

    assert len(queries.list_senses(status="approved")) == 1
    assert queries.list_senses(status="rejected") == []
    assert queries.counts() == [("approved", 1)]


# --- Is 5: ipucu/aciklama panel gorunumu ------------------------------------

def test_rationale_paketi_ayrintida_gorunur():
    """Onayli ipucu/aciklama, ayrinti sayfasinda ipucu + sik aciklamasiyla
    birlikte gorunur."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())
    run_rationale(FakeProvider(answer=rationale_answer()))

    package = queries.package("en:bank:noun")
    assert package["rationale"]["status"] == "approved"
    assert package["rationale"]["stale"] is False
    body = _serve("/cloze/sense?key=en:bank:noun")[2].decode("utf-8")
    assert "ipucu:" in body
    assert "keep or store their money" in body


def test_rationale_bayat_satir_sessizce_gizlenmez():
    """Kabul olcutu (§18): cloze sorusu degisince rationale panelde acikca
    BAYAT gorunur, gizlenmez."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())
    run_rationale(FakeProvider(answer=rationale_answer()))

    conn = schema.open_cloze_db()
    with conn:
        conn.execute("UPDATE sense_cloze_question SET sentence = ?"
                     " WHERE seq = 1",
                     ("I put my savings in a bank every month.",))
    conn.close()

    package = queries.package("en:bank:noun")
    assert package["rationale"]["stale"] is True
    body = _serve("/cloze/sense?key=en:bank:noun")[2].decode("utf-8")
    assert "BAYAT" in body


def test_rationale_paketi_yokken_panel_dusmez():
    """Cloze onayli ama rationale hic kosmamissa sayfa yine 200 doner."""
    seed_all()
    _seed_identity()
    run_cloze(FakeProvider())

    package = queries.package("en:bank:noun")
    assert package["rationale"] is None
    status, _ctype, body = _serve("/cloze/sense?key=en:bank:noun")
    assert status == 200
    assert "Ipucu/aciklama paketi yok" in body.decode("utf-8")


def test_panel_hicbir_yazma_sorgusu_icermez():
    """Duzeltme yolu `review`dir: panel katmani depoya YAZMAZ."""
    writes = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE")
    offenders = []
    for name in sorted(os.listdir(os.path.join(CLOZE_ROOT, "panel"))):
        if not name.endswith(".py"):
            continue
        path = os.path.join(CLOZE_ROOT, "panel", name)
        text = open(path, encoding="utf-8").read().upper()
        if any(f" {word} " in text or f'"{word} ' in text for word in writes):
            offenders.append(path)
    assert offenders == []
